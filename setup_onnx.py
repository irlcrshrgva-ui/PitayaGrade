"""Bundle the complete pinned ONNX web runtime without replacing model weights."""
import argparse
import hashlib
import json
from pathlib import Path

VERSION = '1.19.0'
FILES = ('ort.min.js', 'ort-wasm-simd-threaded.mjs', 'ort-wasm-simd-threaded.wasm')
ROOT = Path(__file__).resolve().parent


def bundle_runtime(package_dir, output_dir):
    package_dir, output_dir = Path(package_dir), Path(output_dir)
    package = json.loads((package_dir / 'package.json').read_text(encoding='utf-8'))
    if package.get('name') != 'onnxruntime-web' or package.get('version') != VERSION:
        raise ValueError(f'Use the complete onnxruntime-web@{VERSION} package')
    contents = {name: (package_dir / 'dist' / name).read_bytes() for name in FILES}
    contents['onnxruntime-LICENSE'] = (ROOT / 'www' / 'onnxruntime-LICENSE').read_bytes()
    if f'ONNX Runtime Web v{VERSION}'.encode() not in contents['ort.min.js'][:200]:
        raise ValueError('JavaScript runtime version mismatch')
    if contents['ort-wasm-simd-threaded.wasm'][:8] != b'\x00asm\x01\x00\x00\x00':
        raise ValueError('Invalid WebAssembly runtime')
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, data in contents.items():
        (output_dir / name).write_bytes(data)
    record = {'package': f'onnxruntime-web@{VERSION}', 'version': VERSION,
              'source': 'https://www.npmjs.com/package/onnxruntime-web/v/' + VERSION,
              'license': 'MIT', 'backend': 'wasm', 'numThreads': 1,
              'files': {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()}}
    (output_dir / 'runtime-assets.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-dir', required=True, type=Path,
                        help='Installed onnxruntime-web package directory, including package.json and dist/.')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'www')
    args = parser.parse_args(argv)
    try:
        bundle_runtime(args.runtime_dir, args.output_dir)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print('Bundled all three matching runtime files. Model weights were not changed.')


if __name__ == '__main__':
    main()
