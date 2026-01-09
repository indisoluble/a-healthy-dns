from setuptools import setup, find_packages

setup(
    name="a_healthy_dns",
    version="0.1.21",
    description="A healthy DNS project",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=["cryptography>=46.0.3,<47.0.0", "dnspython>=2.8.0,<3.0.0"],
    entry_points={
        "console_scripts": ["a-healthy-dns = indisoluble.a_healthy_dns.main:main"]
    },
)
