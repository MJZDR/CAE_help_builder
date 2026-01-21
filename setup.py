from setuptools import setup, find_packages

setup(
    name="cae_doc_builder",
    version="1.0.0",
    packages=find_packages("src"),
    package_dir={"": "src"},
    install_requires=[
        "beautifulsoup4",
        "markdownify",
        "lxml"
    ],
    author="Your Name",
    description="Tool to convert CAE documentation (Ansys, etc.) to Markdown KB",
)
