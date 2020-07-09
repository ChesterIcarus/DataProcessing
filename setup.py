from setuptools import setup
from setuptools import find_packages

with open('README.md', 'r') as readme:
    long_description = readme.read()

with open('requirements.txt', 'r') as requirements:
    packages = requirements.readlines()
    packages = [pkg.strip() for pkg in packages]
     

setup(
    name='icarus-simulation',
    version='1.0',
    author='Benjamin Brownlee',
    author_email='benjamin.brownlee1@gmail.com',
    description='simulation data processing for the icarus project',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/ChesterIcarus/icarus-python',
    packages=find_packages(where='src'),
    install_requires=packages,
    package_dir={'': 'src'},
    include_package_data=True,
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent'
    ],
    python_requires='>=3.7',
)
