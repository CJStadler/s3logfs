# Install s3ql
wget https://bitbucket.org/nikratio/s3ql/downloads/s3ql-2.26.tar.bz2
bzip2 -d s3ql-2.26.tar.bz2
tar -vxf s3ql-2.26.tar
sudo apt install sqlite libsqlite3-dev libfuse-dev pkg-config attr libattr1-dev
pip3 install defusedxml requests dugong llfuse pytest pytest-catchlog
cd s3ql-2.26/
sudo python3 setup.py install
