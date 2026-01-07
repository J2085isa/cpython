package com.alvareztrucking1.app.data

import com.google.gson.annotations.SerializedName

// Modelos de datos para la configuración
data class Configuracion(
    @SerializedName("nombre_empresa") val nombreEmpresa: String,
    @SerializedName("rubro") val rubro: String,
    @SerializedName("direccion") val direccion: String,
    @SerializedName("servicios") val servicios: String,
    @SerializedName("contacto") val contacto: Contacto,
    @SerializedName("redes_sociales") val redesSociales: RedesSociales
)

data class Contacto(
    @SerializedName("telefono") val telefono: String,
    @Serializ/*
 * Copyright 2026 Alvarez Trucking 1, S.A. de C.V.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.alvareztrucking1.app.data
// ... resto del código
edName("correo") val correo: String,
    @SerializedName("sitio_web") val sitioWeb: String
)

data class RedesSociales(
    @SerializedName("kwai") val kwai: String,
    @SerializedName("instagram") val instagram: String,
    @SerializedName("tiktok") val tiktok: String,
    @SerializedName("facebook") val facebook: String
)
# Python for Android

These instructions are only needed if you're planning to compile Python for
Android yourself. Most users should *not* need to do this. Instead, use one of
the tools listed in `Doc/using/android.rst`, which will provide a much easier
experience.


## Prerequisites

First, make sure you have all the usual tools and libraries needed to build
Python for your development machine.

Second, you'll need an Android SDK. If you already have the SDK installed,
export the `ANDROID_HOME` environment variable to point at its location.
Otherwise, here's how to install it:

* Download the "Command line tools" from <https://developer.android.com/studio>.
* Create a directory `android-sdk/cmdline-tools`, and unzip the command line
  tools package into it.
* Rename `android-sdk/cmdline-tools/cmdline-tools` to
  `android-sdk/cmdline-tools/latest`.
* `export ANDROID_HOME=/path/to/android-sdk`

The `android.py` script also requires the following commands to be on the `PATH`:

* `curl`
* `java` (or set the `JAVA_HOME` environment variable)
* `tar`
* `unzip`


## Building

Python can be built for Android on any POSIX platform supported by the Android
development tools, which currently means Linux or macOS. This involves doing a
cross-build where you use a "build" Python (for your development machine) to
help produce a "host" Python for Android.

The easiest way to do a build is to use the `android.py` script. You can either
have it perform the entire build process from start to finish in one step, or
you can do it in discrete steps that mirror running `configure` and `make` for
each of the two builds of Python you end up producing.

The discrete steps for building via `android.py` are:

```sh
./android.py configure-build
./android.py make-build
./android.py configure-host HOST
./android.py make-host HOST
```

`HOST` identifies which architecture to build. To see the possible values, run
`./android.py configure-host --help`.

To do all steps in a single command, run:

```sh
./android.py build HOST
```

In the end you should have a build Python in `cross-build/build`, and an Android
build in `cross-build/HOST`.

You can use `--` as a separator for any of the `configure`-related commands –
including `build` itself – to pass arguments to the underlying `configure`
call. For example, if you want a pydebug build that also caches the results from
`configure`, you can do:

```sh
./android.py build HOST -- -C --with-pydebug
```


## Testing

The test suite can be run on Linux, macOS, or Windows:

* On Linux, the emulator needs access to the KVM virtualization interface, and
  a DISPLAY environment variable pointing at an X server.
* On Windows, you won't be able to do the build on the same machine, so you'll
  have to copy the `cross-build/HOST` directory from somewhere else.

The test suite can usually be run on a device with 2 GB of RAM, but this is
borderline, so you may need to increase it to 4 GB. As of Android
Studio Koala, 2 GB is the default for all emulators, although the user interface
may indicate otherwise. Locate the emulator's directory under `~/.android/avd`,
and find `hw.ramSize` in both config.ini and hardware-qemu.ini. Either set these
manually to the same value, or use the Android Studio Device Manager, which will
update both files.

Before running the test suite, follow the instructions in the previous section
to build the architecture you want to test. Then run the test script in one of
the following modes:

* In `--connected` mode, it runs on a device or emulator you have already
  connected to the build machine. List the available devices with
  `$ANDROID_HOME/platform-tools/adb devices -l`, then pass a device ID to the
  script like this:

  ```sh
  ./android.py test --connected emulator-5554
  ```

* In `--managed` mode, it uses a temporary headless emulator defined in the
  `managedDevices` section of testbed/app/build.gradle.kts. This mode is slower,
  but more reproducible.

  We currently define two devices: `minVersion` and `maxVersion`, corresponding
  to our minimum and maximum supported Android versions. For example:

  ```sh
  ./android.py test --managed maxVersion
  ```

By default, the only messages the script will show are Python's own stdout and
stderr. Add the `-v` option to also show Gradle output, and non-Python logcat
messages.

Any other arguments on the `android.py test` command line will be passed through
to `python -m test` – use `--` to separate them from android.py's own options.
See the [Python Developer's
Guide](https://devguide.python.org/testing/run-write-tests/) for common options
– most of them will work on Android, except for those that involve subprocesses,
such as `-j`.

Every time you run `android.py test`, changes in pure-Python files in the
repository's `Lib` directory will be picked up immediately. Changes in C files,
and architecture-specific files such as sysconfigdata, will not take effect
until you re-run `android.py make-host` or `build`.


## Using in your own app

See `Doc/using/android.rst`.# -*- coding: utf-8 -*-
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
// IMPORTANTE: Primero instala las dependencias necesarias:
// Ejecuta en tu terminal: npm install @google/generative-ai wavefile

// Importamos las bibliotecas requeridas
import { GoogleGenerativeAI, Modality } from "@google/generative-ai";
import * as fs from "node:fs";
import pkg from "wavefile";
const { WaveFile } = pkg;

// CONFIGURA TU CLAVE DE API AQUÍ (la obtienes en Google AI Studio)
const API_KEY = "TU_CLAVE_DE_API_DE_GEMINI_AQUI";
const ai = new GoogleGenerativeAI(API_KEY);

// Definimos el modelo especializado en audio y funciones
const modelo = "gemini-2.5-flash-native-audio";

// ------------------------------
// FUNCIONES QUE PUEDES CONTROLAR
// ------------------------------
// Agrega aquí más funciones según las necesidades de AlvarezTrucking1App
const encender_luces = { 
  name: "encender_luces",
  description: "Enciende las luces del camión o la oficina",
  parameters: {
    type: "object",
    properties: {
      ubicacion: {
        type: "string",
        description: "Ubicación de las luces: camion-123, oficina-central, etc."
      }
    },
    required: ["ubicacion"]
  }
};

const apagar_luces = { 
  name: "apagar_luces",
  description: "Apaga las luces del camión o la oficina",
  parameters: {
    type: "object",
    properties: {
      ubicacion: {
        type: "string",
        description: "Ubicación de las luces: camion-123, oficina-central, etc."
      }
    },
    required: ["ubicacion"]
  }
};

// Agregamos las funciones a las herramientas del modelo
const herramientas = [{ 
  functionDeclarations: [encender_luces, apagar_luces] 
}];

// Configuración: el modelo responderá en formato de audio
const configuracion = {
  responseModalities: [Modality.AUDIO],
  tools: herramientas
};

// ------------------------------
// FUNCIONES DE MANEJO DE SESION
// ------------------------------
async function sesionEnTiempoReal() {
  const colaRespuestas = [];

  // Espera hasta que llegue un mensaje nuevo
  async function esperarMensaje() {
    let listo = false;
    let mensaje = undefined;
    while (!listo) {
      mensaje = colaRespuestas.shift();
      if (mensaje) {
        listo = true;
      } else {
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    }
    return mensaje;
  }

  // Procesa todos los mensajes recibidos
  async function procesarMensajes() {
    const mensajesProcesados = [];
    let listo = false;
    while (!listo) {
      const mensaje = await esperarMensaje();
      mensajesProcesados.push(mensaje);
      
      // Termina si llega contenido del servidor o una llamada a función
      if (mensaje.serverContent || mensaje.toolCall) {
        listo = true;
      }
    }
    return mensajesProcesados;
  }

  // ------------------------------
  // CONECTAMOS CON EL MODELO
  // ------------------------------
  const sesion = await ai.live.connect({
    model: modelo,
    callbacks: {
      onopen: () => {
        console.log("✅ Conexión con Gemini establecida");
      },
      onmessage: (mensaje) => {
        colaRespuestas.push(mensaje);
        console.log("📩 Nuevo mensaje recibido");
      },
      onerror: (error) => {
        console.error("❌ Error en la sesión:", error.message);
      },
      onclose: (razon) => {
        console.log("🔌 Sesión cerrada. Razón:", razon.reason);
      },
    },
    config: configuracion,
  });

  // ------------------------------
  // ENVÍA TU INSTRUCCIÓN AQUÍ
  // ------------------------------
  const instruccionUsuario = "Por favor enciende las luces del camión con placa CAM-789";
  console.log(`💬 Enviando instrucción: ${instruccionUsuario}`);
  sesion.sendClientContent({ turns: [{ parts: [{ text: instruccionUsuario }] }] });

  // Procesamos las respuestas del modelo
  let mensajes = await procesarMensajes();

  // Manejo de llamadas a funciones
  for (const mensaje of mensajes) {
    if (mensaje.toolCall) {
      console.log("🛠️ Se llamó a una herramienta!");
      const respuestasFunciones = [];
      
      for (const llamada of mensaje.toolCall.functionCalls) {
        console.log(`▶️ Ejecutando función: ${llamada.name}`);
        // Aquí puedes agregar el código real para controlar dispositivos
        respuestasFunciones.push({
          id: llamada.id,
          name: llamada.name,
          response: { 
            resultado: "ok",
            mensaje: `Función ${llamada.name} ejecutada correctamente en ${llamada.args.ubicacion}`
          }
        });
      }

      // Enviamos la respuesta de la función al modelo
      console.log("📤 Enviando respuesta de la herramienta...");
      sesion.sendToolResponse({ functionResponses: respuestasFunciones });
    }
  }

  // Obtenemos y guardamos la respuesta de audio
  mensajes = await procesarMensajes();
  const audioCombinado = mensajes.reduce((acumulador, mensaje) => {
    if (mensaje.data) {
      const buffer = Buffer.from(mensaje.data, "base64");
      const arrayEnteros = new Int16Array(buffer.buffer);
      return acumulador.concat(Array.from(arrayEnteros));
    }
    return acumulador;
  }, []);

  // Guardamos el archivo de audio en tu computadora
  if (audioCombinado.length > 0) {
    const archivoAudio = new WaveFile();
    archivoAudio.fromScratch(1, 24000, "16", audioCombinado);
    fs.writeFileSync("respuesta_alvareztrucking.wav", archivoAudio.toBuffer());
    console.log("🎧 Archivo de audio guardado como: respuesta_alvareztrucking.wav");
  }

  // Cerramos la sesión
  sesion.close();
}

// ------------------------------
// EJECUTAMOS EL PROGRAMA
// ------------------------------
async function main() {
  try {
    await sesionEnTiempoReal();
  } catch (error) {
    console.error("❌ Error general del programa:", error.message);
  }
}

main();

