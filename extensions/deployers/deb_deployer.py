######################################################################
# deb_deployer.py
#
# Copyright © 2025 David L. Armstrong
#
# Conan Custom Deployer script that copies each dependency's files
# into a directory tree like the example below. Transitive
# dependencies are included.
#

from conan.tools.files import copy, mkdir, rename, rm
#from conan.errors import ConanException
import os
import subprocess
import shutil

def deploy(graph, output_folder, **kwargs):

    conanfile = graph.root.conanfile

    for name, dependency_item in conanfile.dependencies.items():
        if dependency_item.package_folder is None:
            continue
        process_dependency(conanfile, output_folder, dependency_item)


def process_dependency(conanfile, output_folder, dependency_item):

    info_msg = 'Deployer Processing ' \
             + str(dependency_item) \
             + ': package_folder: ' \
             + str(dependency_item.package_folder)

    conanfile.output.info(info_msg)

    # We expect our toplevel conanfile to accept our `install_prefix` option
    toolchain_prefix = conanfile.options.install_prefix

    # https://www.debian.org/doc/debian-policy/ch-controlfields.html#source
    # Package names (both source and binary) must consist only of lower
    # case letters (a-z), digits (0-9), plus (+) and minus (-) signs, and
    # periods (.). They must be at least two characters long and must
    # start with an alphanumeric character.
    package_prefix = str(toolchain_prefix).lstrip('/').replace('/', '+')

    # Locate the template from the ~/.conan2/extensions/deployers directory
    deployer_rootname = str(os.path.basename(__file__)).rstrip('.py')
    deployer_support_dir = os.path.dirname(__file__)
    deb_template_path = os.path.join(deployer_support_dir, deployer_rootname)

    # We'll name each of our toolchain packages after ourselves.
    # We are "/opt/toolchain", so "make" gets "opt+toolchain-make" to avoid conflict with OS packages.
    dashed_pkg_toolname = f'{ package_prefix }-{ dependency_item.ref.name }'
    dashed_pkg_toolnamever = f'{ dashed_pkg_toolname }-{ dependency_item.ref.version }'
    dachshund_pkg_toolnamever = f'{ dashed_pkg_toolname }_{ dependency_item.ref.version }'
    pkg_root_dst = os.path.join(output_folder, dashed_pkg_toolnamever)

    # If dependency has a install_prefix, we'll copy the files out of that area
    # Otherwise we'll assume it's relocatable and use our toplevel prefix as an
    # install subdirectory and copy to that
    if 'install_prefix' in dependency_item.options:
        tool_prefix = dependency_item.options.install_prefix

        # strip leading '/' off install_prefix
        neutered_prefix = str(tool_prefix).lstrip("/")
        copy_pattern = f'{ neutered_prefix }/*'
        pkg_dst = pkg_root_dst
    else:
        # strip leading '/' off install_prefix
        neutered_prefix = str(toolchain_prefix).lstrip("/")
        copy_pattern = '*'
        pkg_dst = os.path.join(pkg_root_dst, neutered_prefix)

    # Copy the package content out of the Conan cache
    copy(conanfile=conanfile,
         src=dependency_item.package_folder,
         excludes=['conaninfo.txt',
                   'conanmanifest.txt',
                   'conan*.sh',
                   'deactivate_conan*.sh',
                  ],
         dst=pkg_dst,
         pattern=copy_pattern,
        )

    # CONFLICT Avoid - Move typically reused license file paths to package-specific paths
    for license_file in ['COPYING', 'LICENSE', 'LICENSES', 'COPYING.LESSER', 'COPYING.LESSERv3', 'COPYINGv2',]:
        if os.path.exists(os.path.join(pkg_dst, 'licenses', license_file)):
            mkdir(conanfile=conanfile,
                  path=os.path.join(pkg_dst, 'licenses', dependency_item.ref.name),
            )
            rm(conanfile=conanfile,
               folder=os.path.join(pkg_dst, 'licenses', dependency_item.ref.name),
               pattern=os.path.join(license_file),
            )
            rename(conanfile=conanfile,
                   src=os.path.join(pkg_dst, 'licenses', license_file),
                   dst=os.path.join(pkg_dst, 'licenses', dependency_item.ref.name, license_file),
            )
            rm(conanfile=conanfile,
               folder=os.path.join(pkg_dst, 'licenses'),
               pattern=os.path.join(license_file),
            )

    # Copy the template content from the deployer installation
    copy(conanfile=conanfile,
         src=deb_template_path,
         dst=pkg_root_dst,
         pattern="*",
        )

    # NOTE: Mind the `_` in the tarball filename separating pkg name from version!
    # tar czv --exclude debian --file opt+toolchain-make_4.4.1.orig.tar.gz opt+toolchain-make-4.4.1/

    # tar up the deployment copy to use as dch/debuild sources
    subprocess.run(['tar',
                    '--create',
                    '--gzip',
                    '--exclude', 'debian',
                    '--file', os.path.join(output_folder, f'{ dachshund_pkg_toolnamever }.orig.tar.gz'),
                    '--directory', output_folder,
                    os.path.join(dashed_pkg_toolnamever, neutered_prefix)
                   ])

    # pkg_name.dirs file
    dirs_filename = os.path.join(pkg_root_dst, "debian", f'{ dashed_pkg_toolname }.dirs')
    with open(dirs_filename, "w") as dirs_file:
        dirs_file.write(f'{ neutered_prefix }\n')

#TODO
    # - build #/package revision or bootstrap versioning needs to be provided or detected somehow
    # - EMAIL
    # - %changelog ???
#TODO  ./opt+toolchain-make-4.4.1/debian/copyright

    ######################################################################
    # Gather dependency list from conanfile.py for use in control file
    # `Depends:` list with prefixed package names...
    #
    pkg_dep_list = []
    for dep_name, dep_dep in dependency_item.dependencies.items():

        # Check if Conan thinks it's really a runtime dependency we need
        if dep_dep.package_folder is None:
            continue

        # Make sure to add the '-1' package revision as well here!
        prefixed_dep_name = f'{ package_prefix }-{ dep_dep.ref.name }'
        pkg_dep_list.append(f'{ prefixed_dep_name } (= { dep_dep.ref.version }-1)')

    # If the conanfile specifies Apt dependencies, we should just pass them through directly
    if 'apt' in dependency_item._conanfile.system_requires:
        pkg_dep_list.extend(dependency_item._conanfile.system_requires['apt']['install'])
#        for apt_dependency in dependency_item._conanfile.system_requires['apt']['install']:
#            pkg_dep_list.append(f'{ apt_dependency }')

    if pkg_dep_list:
        conanfile.output.info('Final Apt dependencies list:')
        for require_line in pkg_dep_list:
            conanfile.output.info(f'\t{ require_line }')


#Depends: libc6 (>= 2.2.1), default-mta | mail-transport-agent
# ./opt+toolchain-make-4.4.1/debian/control
    pkg_dependencies = ""
    if pkg_dep_list:
        pkg_dependencies = ", " + ", ".join(pkg_dep_list)

    # Detect the value for package Architecture
    # TODO - support noarch pkgs
    dpkg_arch_cmd = [ 'dpkg-architecture',
                      '--query', 'DEB_BUILD_ARCH',
                    ]
    dpkg_arch_proc = subprocess.run( dpkg_arch_cmd, capture_output=True, env={'LANG': ""}, encoding='utf-8',)
    dpkg_arch = dpkg_arch_proc.stdout.split('\n')[0]

    # Generate control file
    control_content = f'Source: { dashed_pkg_toolname }\n' \
                    + f'Maintainer: Conan\n' \
                    + f'XBS-Vendor: Conan\n' \
                    + f'XBS-Packager: conan-system-packaging\n' \
                    + f'Section: misc\n' \
                    + f'Priority: optional\n' \
                    + f'Standards-Version: 4.7.0\n' \
                    + f'Build-Depends: debhelper-compat (= 13)\n' \
                    + f'\n' \
                    + f'Package: { dashed_pkg_toolname }\n' \
                    + f'Architecture: { dpkg_arch }\n' \
                    + f'Depends: ${{misc:Depends}}{ pkg_dependencies }\n' \
                    + f'Description: { dependency_item.description }\n'

#TODO Binary-only package?
#    control_content = f'Package: { dashed_pkg_toolname }\n' \
#                    + f'Version: { dependency_item.ref.version }' \
#                    + f'Architecture: { dpkg_arch }\n' \
#                    + f'Essential: no\n' \
#                    + f'Priority: optional\n' \
#                    + f'Depends: ${{shlibs:Depends}}, ${{misc:Depends}}{ pkg_dependencies }\n' \
#                    + f'Maintainer: Not it\n' \
#                    + f'Description: { dependency_item.description }\n'

    control_filename = os.path.join(pkg_root_dst, "debian", "control")
    with open(control_filename, 'w') as control_file:
        control_file.write(control_content)

#TODO EMAIL
    pkg_ver_revision = str(dependency_item.ref.version) + "-1"
    # export EMAIL=someone@somewhere.com; dch --create -v 1.0-1 --package hello-world
    dch_cmd = [ 'dch',
                '--create',
                '--newversion', pkg_ver_revision,
                '--package', dashed_pkg_toolname,
                'Generated by deb_deployer'
              ]

    conanfile.output.info('Executing dch: ' + str(dch_cmd))
    subprocess.run( dch_cmd,
                    env={'EMAIL': "someone@somewhere.com"},
                    cwd=pkg_root_dst,
                   )

#TODO `dpkg-buildpackage -b`? `dpkg-deb --build my-program_version_architecture`?`
    # Build the package
    debuild_cmd = ['debuild', '-us', '-uc']
    conanfile.output.info('Executing debuild: ' + str(debuild_cmd))
    subprocess.run( debuild_cmd,
                    env={'LANG': ""},
                    cwd=pkg_root_dst,
                   )
