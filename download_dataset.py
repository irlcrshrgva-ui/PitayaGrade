import os
import zipfile
from pathlib import Path

def main():
    # Step 1: Write Kaggle credentials to home directory
    home = Path.home()
    kaggle_dir = home / ".kaggle"
    kaggle_dir.mkdir(exist_ok=True)
    kaggle_json = kaggle_dir / "kaggle.json"

    # Write credentials
    with open(kaggle_json, "w") as f:
        f.write('{"username":"irlcrishregpea","key":"c8fdde8fa7bf9c21ebc7167a83feec4e"}')

    # Set permissions (Windows doesn't enforce chmod 600 the same way, but good practice)
    try:
        os.chmod(kaggle_json, 0o600)
    except Exception:
        pass

    print("Kaggle credentials configured locally!")

    # Step 2: Install kaggle CLI if not available
    try:
        import kaggle
    except ImportError:
        print("Installing kaggle CLI...")
        os.system("pip install --quiet kaggle")
        import kaggle

    # Step 3: Download dataset
    dataset_name = "ceileguce/ph-dragonfruit-dataset"
    output_dir = Path(r"d:\desktop\PitayaGrade\dataset")
    output_dir.mkdir(exist_ok=True)

    print(f"Downloading dataset '{dataset_name}' to {output_dir}...")
    os.system(f'kaggle datasets download -d {dataset_name} -p "{output_dir}"')

    # Step 4: Unzip dataset
    zip_files = list(output_dir.glob("*.zip"))
    if zip_files:
        print(f"Unzipping {zip_files[0]}...")
        with zipfile.ZipFile(zip_files[0], 'r') as zip_ref:
            zip_ref.extractall(output_dir)
        print("Unzip complete!")
        
        # Remove zip file to clean up
        try:
            zip_files[0].unlink()
            print("Cleaned up temporary zip archive.")
        except Exception:
            pass
    else:
        print("No zip file found. Check download logs.")

    print("\nDataset gathering successfully complete!")

if __name__ == "__main__":
    main()
