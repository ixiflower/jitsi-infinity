import urllib.request, os, tarfile, io, shutil

base = 'http://deb.debian.org/debian/pool/main/f/ffmpeg/'
pkgs = [
    ('libavdevice61_7.1.5-0+deb13u1_amd64.deb', 'libavdevice.so.61'),
    ('libavfilter10_7.1.5-0+deb13u1_amd64.deb', 'libavfilter.so.10'),
    ('libavformat61_7.1.5-0+deb13u1_amd64.deb', 'libavformat.so.61'),
    ('libavcodec61_7.1.5-0+deb13u1_amd64.deb', 'libavcodec.so.61'),
    ('libswresample5_7.1.5-0+deb13u1_amd64.deb', 'libswresample.so.5'),
    ('libswscale8_7.1.5-0+deb13u1_amd64.deb', 'libswscale.so.8'),
    ('libavutil59_7.1.5-0+deb13u1_amd64.deb', 'libavutil.so.59'),
]

os.makedirs('/home/lightrec/lib', exist_ok=True)

for pkg_name, so_name in pkgs:
    url = base + pkg_name
    print(f'Downloading {pkg_name}...', flush=True)
    try:
        resp = urllib.request.urlopen(url, timeout=30)
        data = resp.read()
        tmp = f'/tmp/{pkg_name}'
        with open(tmp, 'wb') as f:
            f.write(data)
        
        f = open(tmp, 'rb')
        f.read(8)
        while True:
            header = f.read(60)
            if len(header) < 60:
                break
            name = header[:16].decode().strip()
            size = int(header[48:58].decode().strip())
            if 'data.tar' in name:
                tar_data = f.read(size)
                mode = 'r:xz' if name.endswith('.xz') else 'r'
                tar = tarfile.open(fileobj=io.BytesIO(tar_data), mode=mode)
                for member in tar.getmembers():
                    if '/usr/lib/' in member.name and not member.isdir():
                        print(f'  Extracting {member.name}', flush=True)
                        tar.extract(member, '/tmp/ffmpeg-extracted')
                        src = f'/tmp/ffmpeg-extracted/{member.name}'
                        dest_name = member.name.split('/')[-1]
                        shutil.copy2(src, f'/home/lightrec/lib/{dest_name}')
                        os.chmod(f'/home/lightrec/lib/{dest_name}', 0o644)
                tar.close()
                break
            else:
                f.read(size)
        f.close()
        os.remove(tmp)
    except Exception as e:
        print(f'  Failed: {e}', flush=True)

print('\nLibraries:', sorted(os.listdir('/home/lightrec/lib/')), flush=True)
