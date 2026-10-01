#!/bin/bash
set -e

PACKAGE_NAME="cinnamon-clipboard"
VERSION="1.0.0~rc1"
ARCH="all"
BUILD_DIR="build_deb"

echo "=== Generando paquete Debian para $PACKAGE_NAME v$VERSION ==="

# 1. Limpiar construcciones anteriores
rm -rf "$BUILD_DIR"
rm -f "${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"

# 2. Compilar traducciones
echo "[+] Compilando traducciones gettext..."
msgfmt \
    locale/es/LC_MESSAGES/cinnamon-clipboard.po \
    -o locale/es/LC_MESSAGES/cinnamon-clipboard.mo

# 3. Crear estructura del paquete
echo "[+] Creando estructura de directorios..."

mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/usr/bin"
mkdir -p "$BUILD_DIR/usr/lib/python3/dist-packages/cinnamon_clipboard"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/512x512/apps"
mkdir -p "$BUILD_DIR/usr/share/locale/es/LC_MESSAGES"

# 4. Crear DEBIAN/control
echo "[+] Generando metadata de DEBIAN/control..."

cat <<EOF > "$BUILD_DIR/DEBIAN/control"
Package: $PACKAGE_NAME
Version: $VERSION
Architecture: $ARCH
Maintainer: Pablo / Vaider13 <vaider13@github.com>
Depends: python3, python3-gi, gir1.2-gtk-3.0, gir1.2-xapp-1.0, gir1.2-keybinder-3.0, python3-setproctitle, python3-xlib
Section: utils
Priority: optional
Description: Clipboard manager for Cinnamon and Linux desktops
 Simple, lightweight, and responsive clipboard manager with GTK3, SQLite persistence,
 shortcut support, and privacy filter for password managers.
EOF

# 5. Crear ejecutable
echo "[+] Creando ejecutable en /usr/bin/cinnamon-clipboard..."

cat <<'EOF' > "$BUILD_DIR/usr/bin/cinnamon-clipboard"
#!/bin/sh
exec python3 -m cinnamon_clipboard.app "$@"
EOF

chmod +x "$BUILD_DIR/usr/bin/cinnamon-clipboard"

# 6. Copiar código Python
echo "[+] Copiando código de la aplicación..."

cp -a src/cinnamon_clipboard/. \
    "$BUILD_DIR/usr/lib/python3/dist-packages/cinnamon_clipboard/"

# 7. Copiar icono
if [ -f "data/icons/cinnamon-clipboard.png" ]; then
    echo "[+] Copiando icono..."

    cp data/icons/cinnamon-clipboard.png \
        "$BUILD_DIR/usr/share/icons/hicolor/512x512/apps/cinnamon-clipboard.png"
else
    echo "[!] Advertencia: no se encontró el icono."
fi

# 8. Copiar traducciones
echo "[+] Copiando traducciones..."

cp locale/es/LC_MESSAGES/cinnamon-clipboard.mo \
    "$BUILD_DIR/usr/share/locale/es/LC_MESSAGES/"

# 9. Crear lanzador
echo "[+] Creando lanzador .desktop..."

cat <<EOF > "$BUILD_DIR/usr/share/applications/cinnamon-clipboard.desktop"
[Desktop Entry]
Type=Application
Name=Cinnamon Clipboard
Name[es]=Portapapeles de Cinnamon
Comment=Clipboard manager for Cinnamon
Comment[es]=Gestor de portapapeles para Cinnamon
Exec=cinnamon-clipboard
Icon=cinnamon-clipboard
StartupWMClass=CinnamonClipboard
Terminal=false
Categories=Utility;GTK;
EOF

# 10. Construir paquete
echo "[+] Empaquetando con dpkg-deb..."

dpkg-deb \
    --build \
    --root-owner-group \
    "$BUILD_DIR" \
    "${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"

echo
echo "=== ¡Paquete generado con éxito! ==="
echo "${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
