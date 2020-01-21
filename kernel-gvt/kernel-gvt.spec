# A spec file for building xenlinux Dom0 kernel for Qubes
# Based on the Open SUSE kernel-spec & Fedora kernel-spec.
#

%define variant gvt.qubes
%define plainrel 1
%define rel %{plainrel}.%{variant}
%define version 4.19.94

%define _buildshell /bin/bash
%define build_xen       1

%global cpu_arch x86_64
%define cpu_arch_flavor %cpu_arch

%define kernelrelease %(echo %{version} | sed 's/^3\\.[0-9]\\+$/\\0.0/')-%rel.%cpu_arch
%define my_builddir %_builddir/%{name}-%{version}

%define build_src_dir %my_builddir/linux-%version
%define src_install_dir /usr/src/kernels/%kernelrelease
%define kernel_build_dir %my_builddir/linux-obj
%define vm_install_dir /var/lib/qubes/vm-kernels/%version-%{plainrel}

%define install_vdso 1
%define debuginfodir /usr/lib/debug

# debuginfo build is disabled by default to save disk space (it needs 2-3GB build time)
%define with_debuginfo 0

%if !%{with_debuginfo}
%global debug_package %{nil}
%define setup_config --disable CONFIG_DEBUG_INFO
%else
%define setup_config --enable CONFIG_DEBUG_INFO --disable CONFIG_DEBUG_INFO_REDUCED
%endif

%define name_suffix -gvt
%define patchurl https://raw.githubusercontent.com/QubesOS/qubes-linux-kernel/v%{version}-1

Name:           kernel%{?name_suffix}
Summary:        The Xen Kernel
Version:        %{version}
Epoch:          1000
Release:        %{rel}
License:        GPL v2 only
Group:          System/Kernel
Url:            http://www.kernel.org/
AutoReqProv:    on
BuildRequires:  coreutils module-init-tools sparse
BuildRequires:  qubes-kernel-vm-support
BuildRequires:  dracut
BuildRequires:  busybox
BuildRequires:  bc
BuildRequires:  openssl-devel
BuildRequires:  gcc-plugin-devel
BuildRequires:  elfutils-libelf-devel
BuildRequires:  bison
BuildRequires:  flex
BuildRequires:  e2fsprogs
BuildRequires:  openssl

# gcc with support for BTI mitigation
%if 0%{?fedora} == 23
BuildRequires:  gcc >= 5.3.1-6.qubes1
%else
%if 0%{?fedora} == 25
BuildRequires:  gcc >= 6.4.1-1.qubes1
%else
BuildRequires:  gcc
%endif
%endif

# Needed for building GCC hardened plugins
BuildRequires: gcc-c++

# to use pathfix.py
%if 0%{?fedora} >= 31
BuildRequires: python3-devel
%endif

Provides:       multiversion(kernel)
Provides:       %name = %kernelrelease

Provides:       kernel-xen-dom0
Provides:       kernel-qubes-dom0
Provides:       kernel-qubes-dom0-pvops
Provides:       kernel-drm = 4.3.0
Provides:       kernel-drm-nouveau = 16
Provides:       kernel-modules-extra = %kernelrelease
Provides:       kernel-modeset = 1

Requires(pre):  coreutils gawk
Requires(post): dracut binutils
Requires:       qubes-core-dom0-linux-kernel-install

Conflicts:      sysfsutils < 2.0
# root-lvm only works with newer udevs
Conflicts:      udev < 118
Conflicts:      lvm2 < 2.02.33
Provides:       kernel = %kernelrelease
Provides:       kernel-uname-r = %kernelrelease

BuildRoot:      %{_tmppath}/%{name}-%{version}-build
ExclusiveArch:  x86_64

Source0:	https://mirrors.edge.kernel.org/pub/linux/kernel/v4.x/linux-%{version}.tar.xz
Source16:       %{patchurl}/guards
Source17:       %{patchurl}/apply-patches
Source33:       %{patchurl}/check-for-config-changes
Source34:       %{patchurl}/gen-config
Source100:      %{patchurl}/config-base
Source101:      %{patchurl}/config-qubes
Source102:	config-gvt

Patch0: %{patchurl}/0001-kbuild-AFTER_LINK.patch
Patch1: %{patchurl}/0002-xen-netfront-detach-crash.patch
Patch2: %{patchurl}/0003-mce-hide-EBUSY-initialization-error-on-Xen.patch
Patch3: %{patchurl}/0004-Log-error-code-of-EVTCHNOP_bind_pirq-failure.patch
Patch4: %{patchurl}/0005-pvops-respect-removable-xenstore-flag-for-block-devi.patch
Patch5: %{patchurl}/0006-pvops-xen-blkfront-handle-FDEJECT-as-detach-request-.patch
Patch6: %{patchurl}/0007-block-add-no_part_scan-module-parameter.patch
Patch7: %{patchurl}/0008-xen-Add-RING_COPY_RESPONSE.patch
Patch8: %{patchurl}/0009-xen-netfront-copy-response-out-of-shared-buffer-befo.patch
Patch9: %{patchurl}/0010-xen-netfront-do-not-use-data-already-exposed-to-back.patch
Patch10: %{patchurl}/0011-xen-netfront-add-range-check-for-Tx-response-id.patch
Patch11: %{patchurl}/0012-xen-blkfront-make-local-copy-of-response-before-usin.patch
Patch12: %{patchurl}/0013-xen-blkfront-prepare-request-locally-only-then-put-i.patch
Patch13: %{patchurl}/0014-xen-pcifront-pciback-Update-pciif.h-with-err-and-res.patch
Patch14: %{patchurl}/0015-xen-pciback-add-attribute-to-allow-MSI-enable-flag-w.patch
Patch15: %{patchurl}/0016-drm-change-func-to-better-detect-wether-swiotlb-is-n.patch
Patch16: %{patchurl}/0017-drm-amdgpu-fix-dma-mask-check-in-gmc_v6_0.c.patch
Patch17: xengt-staging-4.19.patch

%description
Qubes Dom0 kernel.

%prep
if ! [ -e %_sourcedir/linux-%version.tar.xz ]; then
    echo "The %name-%version.nosrc.rpm package does not contain the" \
         "complete sources. Please install kernel-source-%version.src.rpm."
    exit 1
fi

SYMBOLS="xen-dom0 pvops"

# Unpack all sources and patches
%autosetup -N -c -T -a 0

mkdir -p %kernel_build_dir

cd linux-%version
%autopatch -p1

%if 0%{?fedora} >= 31
# Mangle /usr/bin/python shebangs to /usr/bin/python3
# Mangle all Python shebangs to be Python 3 explicitly
# -p preserves timestamps
# -n prevents creating ~backup files
# -i specifies the interpreter for the shebang
# This fixes errors such as
# *** ERROR: ambiguous python shebang in /usr/bin/kvm_stat: #!/usr/bin/python. Change it to python3 (or python2) explicitly.
# We patch all sources below for which we got a report/error.
pathfix.py -i "%{__python3} %{py3_shbang_opts}" -p -n \
	tools/kvm/kvm_stat/kvm_stat \
	scripts/show_delta \
	scripts/diffconfig \
	scripts/bloat-o-meter \
	tools/perf/tests/attr.py \
	tools/perf/scripts/python/stat-cpi.py \
	tools/perf/scripts/python/sched-migration.py \
	Documentation
%endif

cd %kernel_build_dir

# Create QubesOS config kernel
/bin/sh %{SOURCE34} %{SOURCE100} %{SOURCE101}
/bin/sh %{SOURCE34} %{SOURCE100} %{SOURCE102}

%build_src_dir/scripts/config \
        --set-str CONFIG_LOCALVERSION -%release.%cpu_arch %{setup_config}

MAKE_ARGS="$MAKE_ARGS -C %build_src_dir O=$PWD"

make prepare $MAKE_ARGS
make scripts $MAKE_ARGS
make scripts_basic $MAKE_ARGS
krel=$(make -s kernelrelease $MAKE_ARGS)

if [ "$krel" != "%kernelrelease" ]; then
    echo "Kernel release mismatch: $krel != %kernelrelease" >&2
    exit 1
fi

make clean $MAKE_ARGS

rm -f source
find . ! -type d -printf '%%P\n' > %my_builddir/obj-files
rm -rf %_builddir/u2mfn
u2mfn_ver=`dkms status u2mfn|tail -n 1|cut -f 2 -d ' '|tr -d ':,:'`
if [ -n "$u2mfn_ver" ]; then
    cp -r /usr/src/u2mfn-$u2mfn_ver %_builddir/u2mfn
fi

%build

cd %kernel_build_dir

# This override tweaks the kernel makefiles so that we run debugedit on an
# object before embedding it.  When we later run find-debuginfo.sh, it will
# run debugedit again.  The edits it does change the build ID bits embedded
# in the stripped object, but repeating debugedit is a no-op.  We do it
# beforehand to get the proper final build ID bits into the embedded image.
# This affects the vDSO images in vmlinux, and the vmlinux image in bzImage.
export AFTER_LINK=\
'sh -xc "/usr/lib/rpm/debugedit -b $$RPM_BUILD_DIR -d /usr/src/debug \
                    -i $@ > $@.id"'

make %{?_smp_mflags} all $MAKE_ARGS CONFIG_DEBUG_SECTION_MISMATCH=y

# Build u2mfn module
if [ -d "%_builddir/u2mfn" ]; then
    make -C %kernel_build_dir M=%_builddir/u2mfn modules
fi

%install

# get rid of /usr/lib/rpm/brp-strip-debug
# strip removes too much from the vmlinux ELF binary
export NO_BRP_STRIP_DEBUG=true
export STRIP_KEEP_SYMTAB='*/vmlinux-*'

# /lib/modules/%kernelrelease-%build_flavor/build will be a stale symlink until the
# kernel-devel package is installed. Don't check for stale symlinks
# in the brp-symlink check:
export NO_BRP_STALE_LINK_ERROR=yes

cd %kernel_build_dir

mkdir -p %buildroot/boot
cp -p System.map %buildroot/boot/System.map-%kernelrelease
cp -p arch/x86/boot/bzImage %buildroot/boot/vmlinuz-%kernelrelease
cp .config %buildroot/boot/config-%kernelrelease

%if %install_vdso
# Install the unstripped vdso's that are linked in the kernel image
make vdso_install $MAKE_ARGS INSTALL_MOD_PATH=%buildroot
%endif

# Create a dummy initramfs with roughly the size the real one will have.
# That way, rpm will know that this package requires some additional
# space in /boot.
dd if=/dev/zero of=%buildroot/boot/initramfs-%kernelrelease.img \
        bs=1M count=20

gzip -c9 < Module.symvers > %buildroot/boot/symvers-%kernelrelease.gz

make modules_install $MAKE_ARGS INSTALL_MOD_PATH=%buildroot
if [ -d "%_builddir/u2mfn" ]; then
    make modules_install $MAKE_ARGS INSTALL_MOD_PATH=%buildroot M=%_builddir/u2mfn
fi

mkdir -p %buildroot/%src_install_dir

rm -f %buildroot/lib/modules/%kernelrelease/build
rm -f %buildroot/lib/modules/%kernelrelease/source
mkdir -p %buildroot/lib/modules/%kernelrelease/build
(cd %buildroot/lib/modules/%kernelrelease ; ln -s build source)
# dirs for additional modules per module-init-tools, kbuild/modules.txt
mkdir -p %buildroot/lib/modules/%kernelrelease/extra
mkdir -p %buildroot/lib/modules/%kernelrelease/updates
mkdir -p %buildroot/lib/modules/%kernelrelease/weak-updates

pushd %build_src_dir
cp --parents `find  -type f -name "Makefile*" -o -name "Kconfig*"` %buildroot/lib/modules/%kernelrelease/build
cp -a scripts %buildroot/lib/modules/%kernelrelease/build
cp -a --parents arch/x86/include %buildroot/lib/modules/%kernelrelease/build/
cp -a include %buildroot/lib/modules/%kernelrelease/build/include
popd

cp Module.symvers %buildroot/lib/modules/%kernelrelease/build
cp System.map %buildroot/lib/modules/%kernelrelease/build
if [ -s Module.markers ]; then
cp Module.markers %buildroot/lib/modules/%kernelrelease/build
fi

rm -rf %buildroot/lib/modules/%kernelrelease/build/Documentation

# Remove useless scripts that creates ERROR with ambiguous shebang
# that are removed too in Fedora
rm -rf %buildroot/lib/modules/%kernelrelease/build/scripts/tracing
rm -f %buildroot/lib/modules/%kernelrelease/build/scripts/spdxcheck.py

# disable GCC plugins for external modules build, to not fail if different gcc
# version is used
sed -e 's/^\(CONFIG_GCC_PLUGIN.*\)=y/# \1 is not set/' .config > \
        %buildroot/lib/modules/%kernelrelease/build/.config

rm -f %buildroot/lib/modules/%kernelrelease/build/scripts/*.o
rm -f %buildroot/lib/modules/%kernelrelease/build/scripts/*/*.o

cp -a scripts/* %buildroot/lib/modules/%kernelrelease/build/scripts/
cp -a include/* %buildroot/lib/modules/%kernelrelease/build/include/
cp -a --parents arch/x86/include/* %buildroot/lib/modules/%kernelrelease/build/
if [ -f tools/objtool/objtool ]; then
    cp -a --parents tools/objtool %buildroot/lib/modules/%kernelrelease/build/
    pushd %build_src_dir
    cp -a --parents tools/objtool %buildroot/lib/modules/%kernelrelease/build/
    cp -a --parents tools/build/Build.include %buildroot/lib/modules/%kernelrelease/build/
    cp -a --parents tools/build/Build %buildroot/lib/modules/%kernelrelease/build/
    cp -a --parents tools/build/fixdep.c %buildroot/lib/modules/%kernelrelease/build/
    cp -a --parents tools/scripts/utilities.mak %buildroot/lib/modules/%kernelrelease/build/
    cp -a --parents tools/lib/str_error_r.c %buildroot/lib/modules/%kernelrelease/build/
    cp -a --parents tools/lib/string.c %buildroot/lib/modules/%kernelrelease/build/
    cp -a --parents tools/lib/subcmd/* %buildroot/lib/modules/%kernelrelease/build/
    popd
fi

# Copy .config to include/config/auto.conf so "make prepare" is unnecessary.
cp %buildroot/lib/modules/%kernelrelease/build/.config %buildroot/lib/modules/%kernelrelease/build/include/config/auto.conf

# Make sure the Makefile and version.h have a matching timestamp so that
# external modules can be built
touch -r %buildroot/lib/modules/%kernelrelease/build/Makefile %buildroot/lib/modules/%kernelrelease/build/include/generated/uapi/linux/version.h
touch -r %buildroot/lib/modules/%kernelrelease/build/.config %buildroot/lib/modules/%kernelrelease/build/include/config/auto.conf

if test -s vmlinux.id; then
cp vmlinux.id %buildroot/lib/modules/%kernelrelease/build/vmlinux.id
else
echo >&2 "*** WARNING *** no vmlinux build ID! ***"
fi

#
# save the vmlinux file for kernel debugging into the kernel-debuginfo rpm
#
%if %{with_debuginfo}
mkdir -p %buildroot%{debuginfodir}/lib/modules/%kernelrelease
cp vmlinux %buildroot%{debuginfodir}/lib/modules/%kernelrelease
%endif

find %buildroot/lib/modules/%kernelrelease -name "*.ko" -type f >modnames

# mark modules executable so that strip-to-file can strip them
xargs --no-run-if-empty chmod u+x < modnames

# Generate a list of modules for block and networking.

fgrep /drivers/ modnames | xargs --no-run-if-empty nm -upA |
sed -n 's,^.*/\([^/]*\.ko\):  *U \(.*\)$,\1 \2,p' > drivers.undef

collect_modules_list()
{
  sed -r -n -e "s/^([^ ]+) \\.?($2)\$/\\1/p" drivers.undef |
  LC_ALL=C sort -u > %buildroot/lib/modules/%kernelrelease/modules.$1
}

collect_modules_list networking \
                         'register_netdev|ieee80211_register_hw|usbnet_probe'
collect_modules_list block \
                         'ata_scsi_ioctl|scsi_add_host|scsi_add_host_with_dma|blk_init_queue|register_mtd_blktrans|scsi_esp_register|scsi_register_device_handler'
collect_modules_list drm \
                         'drm_open|drm_init'
collect_modules_list modesetting \
                         'drm_crtc_init'

# detect missing or incorrect license tags
rm -f modinfo
while read i
do
  echo -n "${i#%buildroot/lib/modules/%kernelrelease/} " >> modinfo
  /sbin/modinfo -l $i >> modinfo
done < modnames

egrep -v \
          'GPL( v2)?$|Dual BSD/GPL$|Dual MPL/GPL$|GPL and additional rights$' \
          modinfo && exit 1

rm -f modinfo modnames

# Move the devel headers out of the root file system
mkdir -p %buildroot/usr/src/kernels
mv %buildroot/lib/modules/%kernelrelease/build/* %buildroot/%src_install_dir/
mv %buildroot/lib/modules/%kernelrelease/build/.config %buildroot/%src_install_dir
rmdir %buildroot/lib/modules/%kernelrelease/build
ln -sf %src_install_dir %buildroot/lib/modules/%kernelrelease/build

# Abort if there are any undefined symbols
msg="$(/sbin/depmod -F %buildroot/boot/System.map-%kernelrelease \
     -b %buildroot -ae %kernelrelease 2>&1)"

if [ $? -ne 0 ] || echo "$msg" | grep  'needs unknown symbol'; then
exit 1
fi

# in case of no firmware built - place empty dir
mkdir -p %buildroot/lib/firmware
mv  %buildroot/lib/firmware %buildroot/lib/firmware-all
mkdir -p %buildroot/lib/firmware
mv  %buildroot/lib/firmware-all %buildroot/lib/firmware/%kernelrelease

# Prepare initramfs for Qubes VM
mkdir -p %buildroot/%vm_install_dir
PATH="/sbin:$PATH" dracut --nomdadmconf --nolvmconf \
    --kmoddir %buildroot/lib/modules/%kernelrelease \
    --modules "kernel-modules qubes-vm-simple" \
    --conf /dev/null --confdir /var/empty \
    -d "xenblk xen-blkfront cdrom ext4 jbd2 crc16 dm_snapshot" \
    %buildroot/%vm_install_dir/initramfs %kernelrelease || exit 1

# workaround for buggy dracut-044 in Fedora 25
# https://bugzilla.redhat.com/show_bug.cgi?id=1431317
# https://github.com/dracutdevs/dracut/issues/194
modules_dep=$(lsinitrd "%buildroot/%vm_install_dir/initramfs" \
    "usr/lib/modules/%kernelrelease/modules.dep")
if [ -z "$modules_dep" ]; then
    tmpdir=$(mktemp -d)
    zcat "%buildroot/%vm_install_dir/initramfs" | cpio -imd -D "$tmpdir" || exit 1
    mv "$tmpdir"/%buildroot/lib/modules/%kernelrelease/kernel \
        "$tmpdir"/lib/modules/%kernelrelease/ || exit 1
    depmod -F %buildroot/boot/System.map-%kernelrelease \
        -b "$tmpdir" -a %kernelrelease || exit 1
    pushd "$tmpdir"
    if [ -n "$SOURCE_DATE_EPOCH" ]; then
        find . -exec touch --no-dereference --date="@${SOURCE_DATE_EPOCH}" {} +
    fi
    find . -print0 | sort -z \
      | cpio --null -R 0:0 -H newc -o --reproducible --quiet \
      | gzip -n > %buildroot/%vm_install_dir/initramfs || exit 1
    popd
fi

cp -p arch/x86/boot/bzImage %buildroot/%vm_install_dir/vmlinuz

# default kernel options for this kernel
def_kernelopts="root=/dev/mapper/dmroot ro nomodeset console=hvc0"
def_kernelopts="$def_kernelopts rd_NO_PLYMOUTH rd.plymouth.enable=0 plymouth.enable=0"
if [ -e /usr/lib/dracut/modules.d/90qubes-vm-simple/xen-scrub-pages-supported ]; then
    # set xen_scrub_pages=0 _only_ when included initramfs does support
    # re-enabling it
    def_kernelopts="$def_kernelopts xen_scrub_pages=0"
fi
echo "$def_kernelopts " > %buildroot/%vm_install_dir/default-kernelopts-common.txt

# Modules for Qubes VM
mkdir -p %buildroot%vm_install_dir/modules
cp -a %buildroot/lib/modules/%kernelrelease %buildroot%vm_install_dir/modules/
mkdir -p %buildroot%vm_install_dir/modules/firmware
cp -a %buildroot/lib/firmware/%kernelrelease %buildroot%vm_install_dir/modules/firmware/

# Include kernel headers for Qubes VM in "/lib/modules" - so kernel-devel
# package will be unnecessary there, regardless of distribution
rm -f %buildroot%vm_install_dir/modules/%kernelrelease/build
cp -a %buildroot/%src_install_dir %buildroot%vm_install_dir/modules/%kernelrelease/build

%if 0%{?fedora} >= 25
# include kernel+initramfs also inside modules.img, for direct kernel boot with
# stubdomain
cp %buildroot%vm_install_dir/vmlinuz %buildroot%vm_install_dir/modules/
cp %buildroot%vm_install_dir/initramfs %buildroot%vm_install_dir/modules/
if [ -n "$SOURCE_DATE_EPOCH" ]; then
    find %buildroot%vm_install_dir/modules \
       -exec touch --no-dereference --date="@${SOURCE_DATE_EPOCH}" {} +
fi
PATH="/sbin:$PATH" mkfs.ext3 -d %buildroot%vm_install_dir/modules \
      -U dcee2318-92bd-47a5-a15d-e79d1412cdce \
      %buildroot%vm_install_dir/modules.img 500M
rm -rf %buildroot%vm_install_dir/modules
%endif

# remove files that will be auto generated by depmod at rpm -i time
for i in alias alias.bin ccwmap dep dep.bin ieee1394map inputmap isapnpmap ofmap pcimap seriomap symbols symbols.bin usbmap
do
  rm -f %buildroot/lib/modules/%kernelrelease/modules.$i
done

%post
/sbin/depmod -a %{kernelrelease}

%posttrans
# with kernel-4.14+ plymouth detects hvc0 serial console and forces text boot
# we simply make plymouth ignore it to recover the splash screen
if [ -f /etc/default/grub ]; then
    if ! grep -q plymouth.ignore-serial-consoles /etc/default/grub; then
        echo 'GRUB_CMDLINE_LINUX="$GRUB_CMDLINE_LINUX plymouth.ignore-serial-consoles"' >> /etc/default/grub
    fi
fi

if [ -f /boot/efi/EFI/qubes/xen.cfg ]; then
    if ! grep -q plymouth.ignore-serial-consoles /boot/efi/EFI/qubes/xen.cfg; then
        sed -i 's/kernel=.*/& plymouth.ignore-serial-consoles/g' /boot/efi/EFI/qubes/xen.cfg
    fi
fi

/bin/kernel-install add %{kernelrelease} /boot/vmlinuz-%{kernelrelease} || exit $?

# grubby (used by new-kernel-pkg) do not understand xen entries in grub2 config
if [ -x /sbin/new-kernel-pkg -a -e /boot/grub2/grub.cfg ]; then
    grub2-mkconfig > /boot/grub2/grub.cfg
fi

%preun
/bin/kernel-install remove %{kernelrelease} /boot/vmlinuz-%{kernelrelease} || exit $?

%files
%defattr(-, root, root)
%ghost /boot/initramfs-%{kernelrelease}.img
/boot/System.map-%{kernelrelease}
/boot/config-%{kernelrelease}
/boot/symvers-%kernelrelease.gz
%attr(0644, root, root) /boot/vmlinuz-%{kernelrelease}
/lib/firmware/%{kernelrelease}
/lib/modules/%{kernelrelease}

%package devel
Summary:        Development files necessary for building kernel modules
License:        GPL v2 only
Group:          Development/Sources
Provides:       multiversion(kernel)
Provides:       %name-devel = %kernelrelease
%if "%{?name_suffix}" != ""
Provides:       kernel-devel = %kernelrelease
%endif
Provides:       kernel-devel-uname-r = %kernelrelease
Requires:       elfutils-libelf-devel
AutoReqProv:    on

%description devel
This package contains files necessary for building kernel modules (and
kernel module packages) against the kernel.

%post devel
if [ -f /etc/sysconfig/kernel ]
then
    . /etc/sysconfig/kernel || exit $?
fi
if [ "$HARDLINK" != "no" -a -x /usr/sbin/hardlink ]
then
    (cd /usr/src/kernels/%{kernelrelease} &&
     /usr/bin/find . -type f | while read f; do
       hardlink -c /usr/src/kernels/*.fc*.*/$f $f
     done)
fi


%files devel
%defattr(-,root,root)
/usr/src/kernels/%{kernelrelease}


%package qubes-vm
Summary:        The Xen Kernel
Version:        %{version}
Release:        %{rel}
License:        GPL v2 only
Group:          System/Kernel
Url:            http://www.kernel.org/
AutoReqProv:    on
BuildRequires:  coreutils module-init-tools sparse
Provides:       multiversion(kernel-qubes-vm)

Provides:       kernel-xen-domU
Provides:       kernel-qubes-domU

Requires(pre):  coreutils gawk
Requires(post): dracut
Requires(post): qubes-core-dom0

Conflicts:      sysfsutils < 2.0
# root-lvm only works with newer udevs
Conflicts:      udev < 118
Conflicts:      lvm2 < 2.02.33
Provides:       kernel-qubes-vm = %kernelrelease

%description qubes-vm
Qubes domU kernel.

%post qubes-vm

%if 0%{?fedora} < 25
mkdir /tmp/qubes-modules-%kernelrelease
truncate -s 500M /tmp/qubes-modules-%kernelrelease.img
mkfs -t ext3 -F /tmp/qubes-modules-%kernelrelease.img > /dev/null
mount /tmp/qubes-modules-%kernelrelease.img /tmp/qubes-modules-%kernelrelease -o loop
cp -a -t /tmp/qubes-modules-%kernelrelease %vm_install_dir/modules/%kernelrelease
mkdir /tmp/qubes-modules-%kernelrelease/firmware
cp -a -t /tmp/qubes-modules-%kernelrelease/firmware %vm_install_dir/modules/firmware/%kernelrelease
cp %vm_install_dir/vmlinuz /tmp/qubes-modules-%kernelrelease/
cp %vm_install_dir/initramfs /tmp/qubes-modules-%kernelrelease/
umount /tmp/qubes-modules-%kernelrelease
rmdir /tmp/qubes-modules-%kernelrelease
mv /tmp/qubes-modules-%kernelrelease.img %vm_install_dir/modules.img
%endif

current_default="$(qubes-prefs default-kernel)"
current_default_path="/var/lib/qubes/vm-kernels/$current_default"
current_default_package="$(rpm --qf '%{NAME}' -qf "$current_default_path")"
if [ "$current_default_package" = "%{name}-qubes-vm" ]; then
# Set kernel as default VM kernel if we are the default package.

# If qubes-prefs isn't installed yet, the default kernel will be set by %post
# of qubes-core-dom0
type qubes-prefs &>/dev/null && qubes-prefs --set default-kernel %version-%plainrel
fi

exit 0

%preun qubes-vm

if [ "`qubes-prefs -g default-kernel`" == "%version-%plainrel" ]; then
    echo "This kernel version is set as default VM kernel, cannot remove"
    exit 1
fi
if qvm-ls --kernel | grep -qw "%version-%plainrel"; then
    echo "This kernel version is used by at least one VM, cannot remove"
    exit 1
fi

exit 0

%files qubes-vm
%defattr(-, root, root)
%dir %vm_install_dir
%if 0%{?fedora} < 25
%ghost %attr(0644, root, root) %vm_install_dir/modules.img
%else
%attr(0644, root, root) %vm_install_dir/modules.img
%endif
%attr(0644, root, root) %vm_install_dir/initramfs
%attr(0644, root, root) %vm_install_dir/vmlinuz
%if 0%{?fedora} < 25
%vm_install_dir/modules
%endif
%attr(0644, root, root) %vm_install_dir/default-kernelopts-common.txt

%changelog
* Sat Dec 14 2019 Qubes OS Team <qubes-devel@groups.google.com>
- For complete changelog see: https://github.com/QubesOS/qubes-

* Sat Dec 14 2019 fepitre-bot <fepitre-bot@qubes-os.org> - 6fb9f41
- Update to kernel-4.19.89

* Sun Dec 01 2019 Marek Marczykowski-Górecki <marmarek@invisiblethingslab.com> - 3ad8270
- Merge remote-tracking branch 'origin/pr/124' into stable-4.19

* Sat Nov 30 2019 fepitre-bot <fepitre-bot@qubes-os.org> - 6692042
- Update to kernel-4.19.86

* Sun Nov 24 2019 Frédéric Pierret (fepitre) <frederic.pierret@qubes-os.org> - 5cf3b2a
- spec: mangle /usr/bin/python shebangs to /usr/bin/python3

* Sat Nov 16 2019 fepitre-bot <fepitre-bot@qubes-os.org> - 4dc1e91
- Update to kernel-4.19.84

* Mon Nov 11 2019 Marek Marczykowski-Górecki <marmarek@invisiblethingslab.com> - 6c00f3b
- Merge remote-tracking branch 'origin/pr/114' into stable-4.19

* Mon Nov 11 2019 Marek Marczykowski-Górecki <marmarek@invisiblethingslab.com> - 07374eb
- Disable GCC plugins for out of tree kernel modules

* Sat Nov 09 2019 fepitre-bot <fepitre-bot@qubes-os.org> - 870975b
- Update to kernel-4.19.82

* Sat Nov 02 2019 fepitre-bot <fepitre-bot@qubes-os.org> - 55de5a6
- Update to kernel-4.19.81

* Sat Oct 19 2019 fepitre-bot <fepitre-bot@qubes-os.org> - 97292cd
- Update to kernel-4.19.80

* Sat Oct 12 2019 fepitre-bot <fepitre-bot@qubes-os.org> - e8db5c9
- Update to kernel-4.19.79

* Sat Oct 05 2019 fepitre-bot <fepitre-bot@qubes-os.org> - 22bc9d2
- Update to kernel-4.19.76

* Sat Sep 21 2019 fepitre-bot <fepitre-bot@qubes-os.org> - 89845eb
- Update to kernel-4.19.74

* Tue Sep 17 2019 Marek Marczykowski-Górecki <marmarek@invisiblethingslab.com> - fd29026
- Merge remote-tracking branch 'origin/pr/92' into stable-4.19

* Sun Sep 15 2019 Marek Marczykowski-Górecki <marmarek@invisiblethingslab.com> - 189588b
- rpm: set default kernel version based on package flavor

* Sat Sep 14 2019 fepitre-bot <fepitre-bot@qubes-os.org> - cd54eb1
- Update to kernel-4.19.72

* Sat Sep 07 2019 fepitre-bot <fepitre-bot@qubes-os.org> - b9d1274
- Update to kernel-4.19.71

* Fri Aug 16 2019 fepitre-bot <fepitre-bot@qubes-os.org> - 80cca5b
- Update to kernel-4.19.67

* Sat Jul 27 2019 fepitre-bot <fepitre-bot@qubes-os.org> - 95ef045
- Update to kernel-4.19.61

* Sat Jul 20 2019 fepitre-bot <fepitre-bot@qubes-os.org> - f3efd1d
- Update to kernel-4.19.59

* Sat Jul 13 2019 fepitre-bot <fepitre-bot@qubes-os.org> - 67040fe
- Update to kernel-4.19.58

* Sat Jul 06 2019 fepitre-bot <fepitre-bot@qubes-os.org> - 009baa7
- Update to kernel-4.19.57

* Sat Jun 29 2019 fepitre-bot <fepitre-bot@qubes-os.org> - 39ce308
- Update to kernel-4.19.56

* Sat Jun 22 2019 fepitre-bot <fepitre-bot@qubes-os.org> - 892ce7b
- Update to kernel-4.19.54

* Sat Jun 15 2019 fepitre-bot <fepitre-bot@qubes-os.org> - cba881e
- Update to kernel-4.19.50

* Mon Jun 10 2019 Marek Marczykowski-Górecki <marmarek@invisiblethingslab.com> - 0db8239
- version 4.19.48-2

* Sun Jun 09 2019 Marek Marczykowski-Górecki <marmarek@invisiblethingslab.com> - d1a6761
- Merge remote-tracking branch 'origin/pr/58' into stable-4.19

* Sun Jun 09 2019 Marek Marczykowski-Górecki <marmarek@invisiblethingslab.com> - 734ee7c
- Support a build without u2mfn module

* Sat Jun 08 2019 fepitre-bot <fepitre-bot@qubes-os.org> - 0bdff73
- Update to kernel-4.19.48

* Sat Jun 01 2019 fepitre-bot <fepitre-bot@qubes-os.org> - 8b4d479
- Update to kernel-4.19.47

* Tue May 28 2019 Marek Marczykowski-Górecki <marmarek@invisiblethingslab.com> - 38d24af
- version 4.19.46-3

* Tue May 28 2019 Marek Marczykowski-Górecki <marmarek@invisiblethingslab.com> - 706876a
- Apply follow up fix for amdgpu driver

* Tue May 28 2019 Marek Marczykowski-Górecki <marmarek@invisiblethingslab.com> - f6b5a20
- version 4.19.46-2

* Tue May 28 2019 Marek Marczykowski-Górecki <marmarek@invisiblethingslab.com> - 606a117
- Really apply the amdgpu patch

* Tue May 28 2019 Marek Marczykowski-Górecki <marmarek@invisiblethingslab.com> - 670e767
- version 4.19.46-1

* Mon May 27 2019 Marek Marczykowski-Górecki <marmarek@invisiblethingslab.com> - 96657ad
- Backport fix for amdgpu driver on Xen PV (including dom0)

* Sat May 25 2019 fepitre-bot <fepitre-bot@qubes-os.org> - 0e4e2cf
- Update to kernel-4.19.45

* Wed May 15 2019 Marek Marczykowski-Górecki <marmarek@invisiblethingslab.com> - fedad27
- version 4.19.43-1

* Wed May 15 2019 Marek Marczykowski-Górecki <marmarek@invisiblethingslab.com> - 02beadc
- Fix setting default kernel for VM

* Sat May 11 2019 fepitre-bot <fepitre-bot@qubes-os.org> - c799530
- Update to kernel-4.19.42

* Sat May 04 2019 fepitre-bot <fepitre-bot@qubes-os.org> - 5e5e03e
- Update to kernel-4.19.39

* Sat Apr 20 2019 fepitre-bot <fepitre-bot@qubes-os.org> - 8fd5151
- Update to kernel-4.19.36

* Sat Apr 06 2019 fepitre-bot <fepitre-bot@qubes-os.org> - d642d1d
- Update to kernel-4.19.34

* Tue Mar 19 2019 Marek Marczykowski-Górecki <marmarek@invisiblethingslab.com> - 738ddf8
- version 4.19.29-1

* Tue Mar 19 2019 Marek Marczykowski-Górecki <marmarek@invisiblethingslab.com> - f390299
- rpm: build modules.img at package build time only on new system

* Tue Mar 19 2019 Frédéric Pierret (fepitre) <frederic.pierret@qubes-os.org> - ad9f337
- plymouth: ignore serial console hvc0 in UEFI

* Tue Mar 19 2019 Frédéric Pierret (fepitre) <frederic.pierret@qubes-os.org> - 4111545
- Ensure the rebuild of grub.cfg with plymouth.ignore-serial-consoles

* Tue Mar 19 2019 Frédéric Pierret (fepitre) <frederic.pierret@qubes-os.org> - cb45298
- plymouth-ignore-serial-consoles: adjusting the method from marmarek suggestion

* Tue Mar 19 2019 Frédéric Pierret (fepitre) <frederic.pierret@qubes-os.org> - ac27fed
- plymouth: ignore serial console hvc0

* Tue Mar 19 2019 Marek Marczykowski-Górecki <marmarek@invisiblethingslab.com> - 6fa02f0
- Include default-kernelopts-common.txt with kernel-specific default options

