Name:           %{tool_name}
Version:        %{tool_version}
Release:        %{build_num}%{?dist}
Summary:        %{tool_summary}

License:        %{tool_license}
Source0:        %{tool_name}-%{tool_version}.tar.gz

Vendor: %{tool_vendor}
Packager: %{tool_packager}

# We do NOT want automatic dependency detection
AutoReqProv:    no

#Requires:       bash
%if 0%{?tool_dependencies:1}
%{tool_dependencies}
%endif

%description
%{tool_description}

%prep
%setup -q

%install
cp -pR * $RPM_BUILD_ROOT

#%clean
#rm -rf $RPM_BUILD_ROOT

%files
%{toolchain_prefix}
%exclude %{toolchain_prefix}/share/info/dir
