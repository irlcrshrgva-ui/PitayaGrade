"""Colab entry point for the reviewed manuscript quality-training workflow.

Upload the project (including scripts/) and reviewed images to the Colab runtime.
From the project directory, run in a notebook cell:

    !python PitayaGrade_Colab_Training.py --manifest research/reviewed-quality.json --run-dir training_results/colab-reviewed-001

Dependencies must be installed separately. This launcher does not configure
credentials, download a dataset, infer labels, or reuse historical results.
"""
import runpy
from pathlib import Path


def main():
    runpy.run_path(str(Path(__file__).with_name('train_models.py')), run_name='__main__')


if __name__ == '__main__':
    main()
