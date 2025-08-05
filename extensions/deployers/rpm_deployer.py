######################################################################
# rpm_deployer.py
#
# Copyright © 2025 David L. Armstrong
# 
# Conan Custom Deployer script that copies each dependency's files
# into a directory tree like the example below. Transitive
# dependencies are included.
#
# This deployer uses the following installation structure to locate
# the templated RPM spec file:
#
# <deployer install dir>
#     ├── rpm_deployer
#     │   └── template-v1.0.0.spec
#     └── rpm_deployer.py
# 
# `conan config install <path|URL>` is recommended for installation.
#
# See project `README.md` for more installation and usage details.
#

from conan.tools.files import copy, mkdir, rename, rm
#from conan.errors import ConanException
import os
import subprocess

def deploy(graph, output_folder, **kwargs):

    conanfile = graph.root.conanfile

    # Set up RPM dev tree in a temporary HOME directory
    orig_HOME = os.environ['HOME']
    rpm_HOME = os.path.join(output_folder, 'RPM_HOME')
    os.environ['HOME'] = rpm_HOME

    # We'll share a single RPM dev tree for all toolchain packages
    mkdir(conanfile=conanfile,
          path=os.path.join(output_folder, 'RPM_HOME'),
         )

    subprocess.run(['rpmdev-setuptree'])

    for name, dependency_item in conanfile.dependencies.items():
        if dependency_item.package_folder is None:
            continue
        process_dependency(conanfile, output_folder, rpm_HOME, dependency_item)

    # restore original $HOME setting
    os.environ['HOME'] = orig_HOME


# Function to ensure we capture any transitive dependencies
def process_dependency(conanfile, output_folder, rpm_HOME, dependency_item):

    info_msg = 'Deployer Processing ' \
             + str(dependency_item) \
             + ': package_folder: ' \
             + str(dependency_item.package_folder)

    conanfile.output.info(info_msg)

    toolchain_prefix = conanfile.options.install_prefix
    package_prefix = str(toolchain_prefix).lstrip('/').replace('/', '-')

    # We'll name each of our toolchain packages after ourselves.
    # We are "/opt/toolchain", so "make" gets "opt+toolchain-make" to avoid conflict with OS packages.
    dashed_pkg_toolname = f'{ package_prefix }-{ dependency_item.ref.name }'
    dashed_pkg_toolnamever = f'{ dashed_pkg_toolname }-{ dependency_item.ref.version }'

    # If dependency has an install_prefix, we'll copy the files out of that area.
    # Otherwise we'll assume it's relocatable and use our toplevel prefix as an
    # install subdirectory and copy to that.
    if 'install_prefix' in dependency_item.options:
        tool_prefix = dependency_item.options.install_prefix

        # strip leading '/' off install_prefix
        neutered_prefix = str(tool_prefix).lstrip("/")
        copy_pattern = f'{ neutered_prefix }/*'
        pkg_dst = os.path.join(output_folder, dashed_pkg_toolnamever)
    else:
        # strip leading '/' off install_prefix
        neutered_prefix = str(toolchain_prefix).lstrip("/")
        copy_pattern = '*'
        pkg_dst = os.path.join(output_folder, dashed_pkg_toolnamever, neutered_prefix)

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

    # tar up the deployment copy to use as rpmbuild sources
    subprocess.run(['tar',
                    '--create',
                    '--gzip',
                    '--file', os.path.join(rpm_HOME, 'rpmbuild', 'SOURCES', f'{ dashed_pkg_toolnamever }.tar.gz'),
                    '--directory', output_folder,
                    os.path.join(dashed_pkg_toolnamever, neutered_prefix)
                   ])

    # rpm spec template populated with information from conanfile
    #TODO
    # - build # or bootstrap versioning needs to be provided or detected somehow
    # - Summary, arch(x86_64, aarch64, noarch, etc)
    # - author, dependencies
    # - %changelog ???

    ###################################################################### 
    # Gather dependency list from conanfile.py for use in RPM spec
    # `Requires:` list with prefixed package names...
    #
    # This is ugly, we assemble a multi-line string so we can pass it
    # in to rpmbuild on the cmdline.
    # 
    # For example:
    #  `rpmbuild -bb --define tool_dependencies 'Requires: bash\nRequires: ssh' package.spec`
    #
    tool_dependencies = []
    for dep_name, dep_dep in dependency_item.dependencies.items():

        # Check if Conan thinks it's really a runtime dependency we need
        if dep_dep.package_folder is None:
            continue

        prefixed_dep_name = f'{ package_prefix }-{ dep_dep.ref.name }'
        tool_dependencies.append(f'Requires: { prefixed_dep_name } = { dep_dep.ref.version }')

    # If the conanfile specifies Yum dependencies, we should just pass them through directly
    if 'yum' in dependency_item._conanfile.system_requires:
        for yum_dependency in dependency_item._conanfile.system_requires['yum']['install']:
            tool_dependencies.append(f'Requires: { yum_dependency }')

    if tool_dependencies:
        conanfile.output.info('Final RPM dependencies list:')
        for require_line in tool_dependencies:
            conanfile.output.info(f'\t{ require_line }')

    ######################################################################
    # Call `rpmbuild` against our parameterized template RPM spec file,
    # passing any of the metadata from `conanfile.py` as necesary.
    #
    # - set QA_RPATHS - Turn off any failing RPATH checks 
    # - disable __brp_mangle_shebangs, it doesn't work for packages like
    #   cmake and causes more harm than good.
    #
    os.environ['QA_RPATHS'] = "0x0020"
    rpmbuild_cmd = [
        'rpmbuild',
        '-bb',
        '--define', f"__brp_mangle_shebangs /bin/true",
        '--define', f"tool_name { dashed_pkg_toolname }",
        '--define', f"tool_version { dependency_item.ref.version }",
        '--define', f"tool_summary { dependency_item.description }",
        '--define', f"tool_description { dependency_item.description }",
        '--define', f"tool_license { dependency_item.license }",
        '--define', f"tool_vendor Conan",
        '--define', f"tool_packager conan-system-packaging",
        '--define', f"toolchain_prefix { toolchain_prefix }",
        '--define', f"build_num 1",
    ]

    if tool_dependencies:
        rpm_tool_dependencies_arg = 'tool_dependencies '

        for require_line in tool_dependencies:
            rpm_tool_dependencies_arg += f'{ require_line }\n'

        rpmbuild_cmd.extend(['--define', rpm_tool_dependencies_arg])

    # Use the RPM spec template provided with the extension
    deployer_rootname = str(os.path.basename(__file__)).rstrip('.py')
    deployer_support_dir = os.path.dirname(__file__)
    spec_template_path = os.path.join(deployer_support_dir, deployer_rootname, 'template-v1.0.0.spec')

    rpmbuild_cmd.append(spec_template_path)

    conanfile.output.info('Executing rpmbuild: ' + str(rpmbuild_cmd))
    subprocess.run(rpmbuild_cmd)

#TODO throw exception on rpmbuild failure
