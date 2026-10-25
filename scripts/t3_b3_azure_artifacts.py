#!/usr/bin/env python3
"""B3 immutable Azure Blob exchange. Azure CLI must be OIDC-authenticated."""
import argparse,hashlib,json,os,pathlib,re,subprocess,tarfile,tempfile
ROLES={'discovery':range(10),'heldout':range(10,20),'stress':range(20,30),'realworld':range(30,40)}
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()
def az(*parts):
 subprocess.run(['az','storage','blob',*parts,'--auth-mode','login','--only-show-errors','-o','none'],check=True)
def ident(args):
 if not all(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,99}',v) for v in (args.experiment,args.family)):
  raise ValueError('Invalid experiment/family')
 role=args.mc_role if args.stage=='montecarlo' else args.stage
 if args.stage=='montecarlo' and role=='realworld':raise ValueError('Real World has no synthetic Monte Carlo')
 if role not in ROLES or args.seed not in ROLES[role] or args.n not in (200,1000,3000):
  raise ValueError('Stage/seed/n contract mismatch')
 if args.stage not in ('montecarlo',role) or (args.stage!='montecarlo' and args.mc_role):
  raise ValueError('Stage role mismatch')
 return role,f'b3/{args.experiment}/{args.stage}/{role}/{args.family}/seed{args.seed:02d}/n{args.n}'
def transfer(args,operation,name,path):
 az(operation,'--account-name',args.account,'--container-name',args.container,
    '--name',name,'--file',str(path),'--overwrite','false')
def publish(args,prefix,role):
 root=pathlib.Path(args.directory).resolve(strict=True)
 files=[]
 for path in sorted(root.rglob('*')):
  if path.is_symlink():raise ValueError('Symlink forbidden')
  if path.is_file():
   files.append({'path':path.relative_to(root).as_posix(),'sha256':sha(path),'bytes':path.stat().st_size})
 if not files:raise ValueError('No result files')
 with tempfile.TemporaryDirectory() as td:
  archive=pathlib.Path(td)/'payload.tar.gz'
  with tarfile.open(archive,'w:gz') as tar:
   for item in files:tar.add(root/item['path'],arcname=item['path'],recursive=False)
  checksum=sha(archive);base=prefix+'/'+checksum
  manifest={'schema':'B3_AZURE_IMMUTABLE_V1','experiment':args.experiment,'stage':args.stage,
            'seed_role':role,'seed':args.seed,'family':args.family,'sample_n':args.n,
            'revision':os.getenv('GITHUB_SHA','unverified-local'),
            'archive_sha256':checksum,'files':files}
  marker=pathlib.Path(td)/'COMMITTED.json'
  marker.write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
  transfer(args,'upload',base+'/payload.tar.gz',archive)
  transfer(args,'upload',base+'/COMMITTED.json',marker)
  print(json.dumps({'status':'PUBLISHED','prefix':base,'sha256':checksum,'files':len(files)}))
def restore(args,prefix,role):
 if not args.sha256 or not re.fullmatch('[0-9a-f]{64}',args.sha256):raise ValueError('SHA256 required')
 dest=pathlib.Path(args.directory).resolve()
 if dest.exists():raise ValueError('Destination already exists')
 base=prefix+'/'+args.sha256
 with tempfile.TemporaryDirectory() as td:
  tmp=pathlib.Path(td);mark=tmp/'COMMITTED.json';archive=tmp/'payload.tar.gz'
  transfer(args,'download',base+'/COMMITTED.json',mark)
  data=json.loads(mark.read_text())
  expected={'schema':'B3_AZURE_IMMUTABLE_V1','experiment':args.experiment,'stage':args.stage,
            'seed_role':role,'seed':args.seed,'family':args.family,
            'sample_n':args.n,'archive_sha256':args.sha256}
  if any(data.get(k)!=v for k,v in expected.items()):raise ValueError('Manifest mismatch')
  transfer(args,'download',base+'/payload.tar.gz',archive)
  if sha(archive)!=args.sha256:raise ValueError('Archive SHA256 mismatch')
  files=data['files'];names={x['path'] for x in files}
  if len(files)!=len(names):raise ValueError('Duplicate file name')
  with tarfile.open(archive,'r:gz') as tar:
   members=tar.getmembers()
   if set(m.name for m in members)!=names or any(
    not m.isfile() or m.name.startswith('/') or '..' in pathlib.PurePosixPath(m.name).parts
    for m in members):raise ValueError('Unsafe archive')
   dest.mkdir(parents=True)
   for m in members:
    path=dest/m.name;path.parent.mkdir(parents=True,exist_ok=True)
    with tar.extractfile(m) as reader,open(path,'xb') as writer:
     for block in iter(lambda:reader.read(8*1024*1024),b''):writer.write(block)
  if any((dest/x['path']).stat().st_size!=x['bytes'] or sha(dest/x['path'])!=x['sha256'] for x in files):
   raise ValueError('File SHA256 mismatch')
  print(json.dumps({'status':'VERIFIED','sha256':args.sha256,'files':len(files)}))
def main():
 p=argparse.ArgumentParser()
 p.add_argument('operation',choices=('upload','download'))
 for flag in ('experiment','stage','family','directory'):p.add_argument('--'+flag,required=True)
 for flag in ('seed','n'):p.add_argument('--'+flag,type=int,required=True)
 p.add_argument('--mc-role');p.add_argument('--sha256')
 p.add_argument('--account',default=os.getenv('B3_AZURE_STORAGE_ACCOUNT'))
 p.add_argument('--container',default=os.getenv('B3_AZURE_CONTAINER'))
 a=p.parse_args()
 if not a.account or not a.container:p.error('Account and container required')
 role,prefix=ident(a)
 (publish if a.operation=='upload' else restore)(a,prefix,role)
if __name__=='__main__':main()
