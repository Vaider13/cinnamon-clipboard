
#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PACKAGE_NAME="cinnamon-clipboard"
SPEC_SOURCE="packaging/rpm/${PACKAGE_NAME}.spec"
VERSION=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' \
    src/cinnamon_clipboard/_version.py)

if [[ -z "$VERSION" ]]; then
    echo "Error: could not read the version from _version.py" >&2
    exit 1
fi

if [[ ! -f "$SPEC_SOURCE" ]]; then
    echo "Error: RPM spec not found: $SPEC_SOURCE" >&2
    exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Error: this script must run inside the Git repository." >&2
    exit 1
fi

TOPDIR="$HOME/rpmbuild"
mkdir -p "$TOPDIR/SOURCES" "$TOPDIR/SPECS"

SPEC_DEST="$TOPDIR/SPECS/${PACKAGE_NAME}.spec"
SOURCE_ARCHIVE="$TOPDIR/SOURCES/${PACKAGE_NAME}-${VERSION}.tar.gz"

echo "=== Building RPM for $PACKAGE_NAME v$VERSION ==="

# Generate a spec with the version taken from the application.
sed -E "s/^Version:[[:space:]].*/Version:        ${VERSION}/" \
    "$SPEC_SOURCE" > "$SPEC_DEST"

# Package the committed source tree.
git archive \
    --format=tar.gz \
    --prefix="${PACKAGE_NAME}-${VERSION}/" \
    HEAD > "$SOURCE_ARCHIVE"

echo "[+] Building RPM and source RPM..."

rpmbuild -ba "$SPEC_DEST" \
    --define "_topdir $TOPDIR"

echo
echo "=== RPM build finished ==="
echo "Binary RPMs: $TOPDIR/RPMS/"
echo "Source RPMs: $TOPDIR/SRPMS/"
