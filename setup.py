import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

exec(open('cloudos_cli/_version.py').read())
setuptools.setup(
    name="cloudos_cli",
    version=__version__,
    author="David Piñeyro",
    author_email="david.pineyro@lifebit.ai",
    description="Python package for interacting with CloudOS",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/lifebit-ai/cloudos-cli",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    ],
    python_requires='>=3.9',
    entry_points={"console_scripts": [
        "cloudos=cloudos_cli.__main__:run_cloudos_cli"
    ]},
    install_requires=["click>=8.0.1", "rich-click>=1.8.2", "pandas>=1.3.4", "numpy>=1.26.4", "requests>=2.26.0"],
    extras_require={
        "test": ["pytest", "mock", "responses", "requests_mock"]
    },
    include_package_data=True
)
