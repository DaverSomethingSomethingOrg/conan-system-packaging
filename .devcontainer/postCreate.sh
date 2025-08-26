#!/bin/bash

. /etc/os-release

case "${ID}" in
    ubuntu | debian)
        # Official `python` image is Debian based.
#        export DEBIAN_FRONTEND=noninteractive
#        apt-get install --no-install-recommends -y \
#            sudo \
#            build-essential \
#            devscripts \
#            debhelper \
#            fakeroot \
#            binutils \
#            wget \
#            vim
#            # debhelper, cdbs, quilt, pbuilder, sbuild, lintian, svn-buildpackage, git-buildpackage
#
#        pip install --no-cache-dir --break-system-packages -r requirements.txt
        ;;
    almalinux)
        # For RH* support we use AlmaLinux
        # VS Code requires git so we do that in Dockerfile before we get here
#        yum install --enablerepo crb -y \
#            tree \
#            wget \
#            rpmdevtools \
#            rpmlint \
#            perl-File-Compare \
#            perl-FindBin \
#            perl-IPC-Cmd \
#            perl-Digest-SHA \
#            perl-threads \
#            perl-Thread-Queue \
#            perl-open \
#            texinfo
#
#        pip install --no-cache-dir -r requirements.txt
        ;;
    # Otherwise assume the container image comes fully loaded I guess
esac

#pip install --no-cache-dir --break-system-packages -r requirements.txt

# Initialize Conan settings
#TODO git clone our Conan Confg repo here I guess?
#conan profile detect