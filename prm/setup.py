from setuptools import setup, find_packages

setup(
    name='prm',
    install_requires=[
        'setuptools',
        'scikit-learn==0.20.0',
        'sklearn==0.0',
        'scipy==1.1.0',
        'pandas==0.23.4',
    ],
    tests_require=[
        'flake8',
    ],
    packages=find_packages(),
)
