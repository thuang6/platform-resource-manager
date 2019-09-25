FROM centos:7

RUN yum install -y epel-release
RUN sed -i s/#baseurl/baseurl/g /etc/yum.repos.d/*.repo && sed -i s/metalink/#metalink/g /etc/yum.repos.d/*.repo
RUN yum install -y python3-3.6.8-10.el7.x86_64 git make which
RUN python3.6 -m pip install pipenv --proxy=$https_proxy
RUN git clone --branch 0.8.x https://github.com/intel/platform-resource-manager
WORKDIR ./platform-resource-manager
RUN git submodule update --init
WORKDIR ./prm
ARG LC_ALL=en_US.utf-8
ARG LANG=en_US.utf-8
RUN make venv
RUN make package
