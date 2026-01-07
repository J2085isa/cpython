# This script must be sourced with the following variables already set:
: "${ANDROID_HOME:?}"  # Path to Android SDK
: "${HOST:?}"  # GNU target triplet

# You may also override the following:
: "${api_level:=24}"  # Minimum Android API level the build will run on
: "${PREFIX:-}"  # Path in which to find required libraries


# Print all messages on stderr so they're visible when running within build-wheel.
log() {
    echo "$1" >&2
}

fail() {
    log "$1"
    exit 1
}

# When moving to a new version of the NDK, carefully review the following:
#
# * https://developer.android.com/ndk/downloads/revision_history
#
# * https://android.googlesource.com/platform/ndk/+/ndk-rXX-release/docs/BuildSystemMaintainers.md
#   where XX is the NDK version. Do a diff against the version you're upgrading from, e.g.:
#   https://android.googlesource.com/platform/ndk/+/ndk-r25-release..ndk-r26-release/docs/BuildSystemMaintainers.md
ndk_version=27.1.12297006

ndk=$ANDROID_HOME/ndk/$ndk_version
if ! [ -e "$ndk" ]; then
    log "Installing NDK - this may take several minutes"
    yes | "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" "ndk;$ndk_version"
fi

if [ "$HOST" = "arm-linux-androideabi" ]; then
    clang_triplet=armv7a-linux-androideabi
else
    clang_triplet="$HOST"
fi

# These variables are based on BuildSystemMaintainers.md above, and
# $ndk/build/cmake/android.toolchain.cmake.
toolchain=$(echo "$ndk"/toolchains/llvm/prebuilt/*)
export AR="$toolchain/bin/llvm-ar"
export AS="$toolchain/bin/llvm-as"
export CC="$toolchain/bin/${clang_triplet}${api_level}-clang"
export CXX="${CC}++"
export LD="$toolchain/bin/ld"
export NM="$toolchain/bin/llvm-nm"
export RANLIB="$toolchain/bin/llvm-ranlib"
export READELF="$toolchain/bin/llvm-readelf"
export STRIP="$toolchain/bin/llvm-strip"

# The quotes make sure the wildcard in the `toolchain` assignment has been expanded.
for path in "$AR" "$AS" "$CC" "$CXX" "$LD" "$NM" "$RANLIB" "$READELF" "$STRIP"; do
    if ! [ -e "$path" ]; then
        fail "$path does not exist"
    fi
done

export CFLAGS="-D__BIONIC_NO_PAGE_SIZE_MACRO"
export LDFLAGS="-Wl,--build-id=sha1 -Wl,--no-rosegment -Wl,-z,max-page-size=16384"

# Unlike Linux, Android does not implicitly use a dlopened library to resolve
# relocations in subsequently-loaded libraries, even if RTLD_GLOBAL is used
# (https://github.com/android/ndk/issues/1244). So any library that fails to
# build with this flag, would also fail to load at runtime.
LDFLAGS="$LDFLAGS -Wl,--no-undefined"

# Many packages get away with omitting -lm on Linux, but Android is stricter.
LDFLAGS="$LDFLAGS -lm"

# -mstackrealign is included where necessary in the clang launcher scripts which are
# pointed to by $CC, so we don't need to include it here.
if [ "$HOST" = "arm-linux-androideabi" ]; then
    CFLAGS="$CFLAGS -march=armv7-a -mthumb"
fi

if [ -n "${PREFIX:-}" ]; then
    abs_prefix="$(realpath "$PREFIX")"
    CFLAGS="$CFLAGS -I$abs_prefix/include"
    LDFLAGS="$LDFLAGS -L$abs_prefix/lib"

    export PKG_CONFIG="pkg-config --define-prefix"
    export PKG_CONFIG_LIBDIR="$abs_prefix/lib/pkgconfig"
fi

# When compiling C++, some build systems will combine CFLAGS and CXXFLAGS, and some will
# use CXXFLAGS alone.
export CXXFLAGS="$CFLAGS"

# Use the same variable name as conda-build
if [ "$(uname)" = "Darwin" ]; then
    CPU_COUNT="$(sysctl -n hw.ncpu)"
    export CPU_COUNT
else
    CPU_COUNT="$(nproc)"
    export CPU_COUNT
fi
# -*- coding: utf-8 -*-
"""
PROYECTO ALVAREZTRUCKING1 - INTEGRADO EN REPOSITORIO CPython
Descripción: Script para gestión de redes sociales y datos empresariales
Autor: [Tu nombre]
Fecha: 2026-01-07
Versión: 1.2
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional

# Rutas relativas dentro del repositorio CPython
RUTA_CONFIG = os.path.join(os.path.dirname(__file__), "config", "configuracion.json")
RUTA_DATOS = os.path.join(os.path.dirname(__file__), "datos")

# Crear carpeta de datos si no existe
os.makedirs(RUTA_DATOS, exist_ok=True)


# -------------------------- CLASE: CARGA DE CONFIGURACIÓN --------------------------
class CargadorConfiguracion:
    """Carga datos fijos de la empresa desde archivo JSON"""
    @staticmethod
    def cargar() -> Dict:
        try:
            with open(RUTA_CONFIG, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise Exception(f"Archivo de configuración no encontrado en {RUTA_CONFIG}")


# -------------------------- CLASE: ANALIZADOR DE PERFILES --------------------------
class AnalizadorRedesSociales:
    """Analiza y almacena datos de perfiles empresariales"""
    def __init__(self):
        self.config = CargadorConfiguracion.cargar()
        self.nombre_principal = self.config["nombre_empresa"]
        self.datos_perfiles: Dict[str, Dict] = {}
        self.datos_empresa: Dict = {}

    def cargar_datos_perfil(self, plataforma: str, seguidores: int, siguiendo: int, me_gusta: int):
        """Carga datos de perfiles con descripción desde configuración"""
        plataforma = plataforma.lower()
        descripcion = (
            f"{self.nombre_principal} - {self.config['rubro']} en {self.config['direccion']} 🚚 | "
            f"{self.config['servicios']} | Contáctanos: {self.config['contacto']['telefono']}"
        )

        self.datos_perfiles[plataforma] = {
            "nombre_usuario": self.config["redes_sociales"][plataforma],
            "seguidores": seguidores,
            "siguiendo": siguiendo,
            "me_gusta_totales": me_gusta,
            "descripcion": descripcion,
            "fecha_analisis": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "hashtags_destacados": self._obtener_hashtags(plataforma)
        }

    def cargar_datos_empresa(self):
        """Carga datos empresariales desde configuración"""
        self.datos_empresa = {
            "nombre": self.nombre_principal,
            "rubro": self.config["rubro"],
            "direccion": self.config["direccion"],
            "servicios": self.config["servicios"],
            "contacto": self.config["contacto"],
            "horario_atencion": "Lunes a Viernes: 08:00 - 18:00 | Sábados: 09:00 - 14:00"
        }

    def _obtener_hashtags(self, plataforma: str) -> list:
        """Hashtags personalizados por plataforma"""
        hashtags_base = ["#AlvarezTrucking1", "#Transporte", "#Logistica", "#Saltillo", "#Coahuila"]
        plataforma_hashtags = {
            "kwai": ["#KwaiEmpresarial", "#TransporteMexicano"],
            "instagram": ["#InstagramEmpresarial", "#LogisticaMexicana"],
            "tiktok": ["#TikTokNegocios", "#Camiones"],
            "facebook": ["#FacebookEmpresarial", "#EmpresaMexicana"]
        }
        return hashtags_base + plataforma_hashtags.get(plataforma, [])

    def generar_resumen_completo(self) -> str:
        """Genera reportes en la carpeta datos/"""
        resumen_texto = f"=== RESUMEN ALVAREZTRUCKING1 - REDES SOCIALES ===\n"
        resumen_texto += f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

        # Datos de la empresa
        resumen_texto += "--- DATOS EMPRESARIALES ---\n"
        resumen_texto += f"Nombre: {self.datos_empresa['nombre']}\n"
        resumen_texto += f"Rubro: {self.datos_empresa['rubro']}\n"
        resumen_texto += f"Contacto: {self.datos_empresa['contacto']['telefono']} | {self.datos_empresa['contacto']['correo']}\n\n"

        # Datos de perfiles
        resumen_texto += "--- PERFILES POR PLATAFORMA ---\n"
        for plataforma, datos in self.datos_perfiles.items():
            resumen_texto += f"\n> {plataforma.upper()}\n"
            resumen_texto += f"  Usuario: {datos['nombre_usuario']}\n"
            resumen_texto += f"  Seguidores: {datos['seguidores']}\n"
            resumen_texto += f"  Hashtags: {' '.join(datos['hashtags_destacados'])}\n"

        # Guardar archivos
        nombre_archivo = f"resumen_{self.nombre_principal}_{datetime.now().strftime('%Y%m%d')}"
        with open(os.path.join(RUTA_DATOS, f"{nombre_archivo}.txt"), "w", encoding="utf-8") as f_txt:
            f_txt.write(resumen_texto)
        
        with open(os.path.join(RUTA_DATOS, f"{nombre_archivo}.json"), "w", encoding="utf-8") as f_json:
            json.dump({
                "empresa": self.datos_empresa,
                "perfiles": self.datos_perfiles
            }, f_json, indent=2, ensure_ascii=False)

        return resumen_texto


# -------------------------- CLASE: GENERADOR DE PUBLICACIONES --------------------------
class GeneradorPublicaciones:
    """Genera plantillas adaptadas a la empresa"""
    def __init__(self):
        self.config = CargadorConfiguracion.cargar()
        self.plantillas: Dict[str, Dict] = {
            "kwai": {
                "servicio": "📦 Ofrecemos {servicio} en {ubicacion}!\nContáctanos: {telefono}\n{hashtags}",
                "novedad": "🚚 ¡Nueva unidad en nuestra flota! 🎉\nMás capacidad para tu mercancía\n{hashtags}",
                "testimonio": "🙌 Cliente {cliente}: {comentario}\nGracias por confiar en nosotros!\n{hashtags}"
            },
            "instagram": {
                "foto_flota": "📸 Conoce nuestra flota de camiones\n{descripcion}\n{hashtags}\n📞 {telefono}",
                "oferta": "📢 OFERTA ESPECIAL! Descuento en envíos a {destino}\nValido hasta {fecha_limite}\n{hashtags}",
                "reel": "¿Cómo gestionamos tus envíos? 🎬 Mira nuestro proceso\n{hashtags}"
            },
            "tiktok": {
                "flota": "Conoce nuestras unidades 🚚💨\n{contenido}\n{hashtags}",
                "tutorial": "¿Cómo preparar tu mercancía? 📦\n{contenido}\n{hashtags}",
                "evento": "¡Estuvimos en {evento}! 🤝 Conociendo aliados\n{hashtags}"
            },
            "facebook": {
                "publicacion": "✅ {servicio} confiable en {ubicacion}\n{descripcion}\nCotiza aquí: {correo}\n{hashtags}",
                "evento": "📅 ¡Feria de Logística de Saltillo! 📍 Stand {stand}\nFecha: {fecha}\nVisítanos!\n{hashtags}",
                "aviso": "⚠️ Aviso: Horarios especiales en {periodo}\n{informacion}\n{hashtags}"
            }
        }

    def crear_publicacion(self, plataforma: str, tipo: str, **kwargs) -> str:
        """Genera publicación con datos de la empresa"""
        plataforma = plataforma.lower()
        if plataforma not in self.plantillas or tipo not in self.plantillas[plataforma]:
            return "[ERROR] Tipo o plataforma no válidos"

        # Agregar datos de la empresa si no se proporcionan
        kwargs.setdefault("telefono", self.config["contacto"]["telefono"])
        kwargs.setdefault("correo", self.config["contacto"]["correo"])
        kwargs.setdefault("hashtags", " ".join([
            "#AlvarezTrucking1", "#Transporte", "#Logistica", f"#{plataforma.capitalize()}"
        ]))

        return self.plantillas[plataforma][tipo].format(**kwargs)


# -------------------------- EJECUCIÓN PRINCIPAL --------------------------
if __name__ == "__main__":
    print("=== INICIANDO GESTIÓN ALVAREZTRUCKING1 ===")

    # 1. Cargar y analizar datos
    analizador = AnalizadorRedesSociales()
    analizador.cargar_datos_empresa()
    
    # Cargar métricas de redes sociales
    analizador.cargar_datos_perfil("Kwai", 2800, 150, 12500)
    analizador.cargar_datos_perfil("Instagram", 5400, 320, 38200)
    analizador.cargar_datos_perfil("TikTok", 3900, 210, 26700)
    analizador.cargar_datos_perfil("Facebook", 4200, 180, 23100)

    # Generar resumen
    print("\n--- RESUMEN GENERADO ---")
    print(analizador.generar_resumen_completo())
    print(f"\nReportes guardados en: {RUTA_DATOS}")

    # 2. Generar ejemplos de publicaciones
    generador = GeneradorPublicaciones()
    print("\n--- EJEMPLOS DE PUBLICACIONES ---")
    
    pub_insta = generador.crear_publicacion(
        plataforma="Instagram",
        tipo="foto_flota",
        descripcion="Unidades equipadas con tecnología de seguimiento GPS para mayor seguridad",
        hashtags="#AlvarezTrucking1 #Transporte #Logistica #Saltillo #FlotaModerna"
    )
    print("> INSTAGRAM:\n", pub_insta, "\n")

    pub_tiktok = generador.crear_publicacion(
        plataforma="TikTok",
        tipo="tutorial",
        contenido="Empaqueta tu mercancía con materiales resistentes y etiqueta claramente el destino",
        hashtags="#AlvarezTrucking1 #TikTok #Logistica #Consejos #Transporte"
    )
    print("> TIKTOK:\n", pub_tiktok)

    print("\n=== PROCESO COMPLETADO ===")
