import setuptools

setuptools.setup(
    name='churn',
    version='0.0.1',
    description='Pre-processing tools and model definitions for building churn prediction tools.',
    author='Marios Koulakis',
    classifiers=[
        'Development Status :gst: 3 - Alpha ',
        'Intended Audience :: Education',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License'
    ],
    keywords=[
        'churn',
        'deep learning',
        'retention',
        'time series'
        'unsupervised learning',
    ],
    packages=['churn'],
    install_requires=[
        'lightgbm',
        'tensorflow',
        'matplotlib',
        'numpy',
        'sqlalchemy',
        'pandas',
        'psycopg2-binary',
        'seaborn',
        'sklearn',
        'tqdm',
    ],
    python_requires='>=3.6'
)

