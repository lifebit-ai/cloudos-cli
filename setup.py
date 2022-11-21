import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

exec(open('cloudos/_version.py').read())
setuptools.setup(
    name="cloudos",
    version=__version__,
    author="David Piñeyro",
    author_email="davidp@lifebit.ai",
    description="Python package for interacting with CloudOS",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/lifebit-ai/cloudos-cli/cloudos",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires='>=3.8',
    entry_points={"console_scripts": [
        "cloudos=cloudos.__main__:run_cloudos_cli"
    ]},
    include_package_data=True
)
