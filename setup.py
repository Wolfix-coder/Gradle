from setuptools import setup, find_packages

setup(
    name='telegram-order-bot',
    version='0.1.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'aiogram',
        'python-dotenv',
        'aiosqlite',
        'asyncio',
    ],
    author='Pandas',
    author_tg='@Pandas_san',
    description='Telegram Bot for Order Management',
    long_description=open('README.md').read() if open('README.md') else '',
    long_description_content_type='text/markdown',
    python_requires='>=3.8',
    classifiers=[
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'License :: OSI Approved :: MIT License',
    ],
    entry_points={
        'console_scripts': [
            'telegram-bot=bot.main:main',
        ],
    },
)