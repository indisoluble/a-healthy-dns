from setuptools import setup, find_packages

setup(
    name="a_healthy_dns",
    version="0.1.6",
    description="A healthy DNS project",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=["cryptography>=44.0.2,<45.0.0", "dnspython>=2.7.0,<3.0.0"],
    entry_points={
        "console_scripts": ["a-healthy-dns = indisoluble.a_healthy_dns.main:main"]
    },
)
