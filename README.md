# Conan System Packaging

This repository contains extensions for Conan to generate RPM and .deb
system packages.

!!! note annotate "Reference"

    - https://docs.conan.io/2/reference/extensions.html
    - https://github.com/conan-io/conan-extensions

## Installation and Setup

### Conan config install

To install the extensions, use [`conan config install`](https://docs.conan.io/2/reference/commands/config.html).

```bash
$ conan config install https://github.com/DaverSomethingSomethingOrg/conan-system-packaging.git
Trying to clone repo: https://github.com/DaverSomethingSomethingOrg/conan-system-packaging.git
Repo cloned!
Copying file deb_deployer.py to /home/conan_user/.conan2/extensions/deployers
Copying file rpm_deployer.py to /home/conan_user/.conan2/extensions/deployers
Copying file Makefile to /home/conan_user/.conan2/extensions/deployers/deb_deployer
Copying file rules to /home/conan_user/.conan2/extensions/deployers/deb_deployer/debian
Copying file copyright to /home/conan_user/.conan2/extensions/deployers/deb_deployer/debian
Copying file format to /home/conan_user/.conan2/extensions/deployers/deb_deployer/debian/source
Copying file template-v1.0.0.spec to /home/conan_user/.conan2/extensions/deployers/rpm_deployer
$ 
```

### Custom Conan profile

Add an `install_prefix` option to your Conan profile.

```none hl_lines="10-11" title="/home/conan_user/.conan2/profiles/optToolchain"
[settings]
arch=armv8
build_type=Release
compiler=gcc
compiler.cppstd=gnu17
compiler.libcxx=libstdc++11
compiler.version=11
os=Linux

[options]
*:install_prefix=/opt/toolchain
```

## Sample Usage

```bash
$ conan install --build=missing .

$ conan install --deployer-folder=rpm_deploy \
                --deployer=rpm_deployer \
                --profile=optToolchain \
                .

$ conan install --deployer-folder=deb_deploy \
                --deployer=deb_deployer \
                --profile=optToolchain \
                .
```

## Sample Directory Tree Output

```none
rpm_deploy
├── opt_toolchain-gcc-15.1.0
│   └── opt/toolchain
│       ├── bin
│       ├── include
│       ├── lib
│       ├── lib64
│       ├── libexec
│       └── share
└── opt_toolchain-gmp-6.3.0
    └── opt/toolchain
        ├── include
        ├── lib
        └── licenses
```

```none
rpm_deploy/RPM_HOME
└── rpmbuild
    ├── RPMS
    │   └── aarch64
    │       ├── opt_toolchain-gcc-15.1.0-1.el9.aarch64.rpm
    │       ├── opt_toolchain-gmp-6.3.0-1.el9.aarch64.rpm
    │       ├── opt_toolchain-isl-0.26-1.el9.aarch64.rpm
    │       ├── opt_toolchain-make-4.4.1-1.el9.aarch64.rpm
    │       ├── opt_toolchain-mpc-1.2.0-1.el9.aarch64.rpm
    │       ├── opt_toolchain-mpfr-4.2.0-1.el9.aarch64.rpm
    │       └── opt_toolchain-zlib-1.3.1-1.el9.aarch64.rpm
    └── SOURCES
        ├── opt_toolchain-gcc-15.1.0.tar.gz
        ├── opt_toolchain-gmp-6.3.0.tar.gz
        ├── opt_toolchain-isl-0.26.tar.gz
        ├── opt_toolchain-make-4.4.1.tar.gz
        ├── opt_toolchain-mpc-1.2.0.tar.gz
        ├── opt_toolchain-mpfr-4.2.0.tar.gz
        └── opt_toolchain-zlib-1.3.1.tar.gz
```

## License and Copyright

Copyright © 2025 David L. Armstrong

[Apache-2.0](LICENSE.txt)
