# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'body_text_extraction/VERSION'),'rb') as f:
    version = f.read().decode("ascii").strip()


setup(
    name='body_text_extraction',
    version=version,
    description='DOM tree-based body text extractor.',
    author='atsuhiro.narita',
    author_email='alayashiki@gmail.com',
    license='MIT',
    classifiers=[
        'Programming Language :: Python :: 3.4',
        'Topic :: Text Processing :: Markup :: HTML'
    ],
    keywords='html content',
    packages=find_packages(exclude=['bin','test']),
    install_requires=[
        'beautifulsoup4==4.3.2',
        'html5lib==0.99999'
        ]

)

