"""
List of optional components.
"""

__author__ = "Steve Dower <steve.dower@python.org>"
__version__ = "3.8"


__all__ = []


def public(f):
    __all__.append(f.__name__)
    return f


OPTIONS = {
    "stable": {"help": "stable ABI stub"},
    "pip": {"help": "pip"},
    "pip-user": {"help": "pip.ini file for default --user"},
    "tcltk": {"help": "Tcl, Tk and tkinter"},
    "idle": {"help": "Idle"},
    "tests": {"help": "test suite"},
    "tools": {"help": "tools"},
    "venv": {"help": "venv"},
    "dev": {"help": "headers and libs"},
    "symbols": {"help": "symbols"},
    "underpth": {"help": "a python._pth file", "not-in-all": True},
    "launchers": {"help": "specific launchers"},
    "appxmanifest": {"help": "an appxmanifest"},
    "props": {"help": "a python.props file"},
    "nuspec": {"help": "a python.nuspec file"},
    "chm": {"help": "the CHM documentation"},
    "html-doc": {"help": "the HTML documentation"},
    "freethreaded": {"help": "freethreaded binaries", "not-in-all": True},
    "alias": {"help": "aliased python.exe entry-point binaries"},
    "alias3": {"help": "aliased python3.exe entry-point binaries"},
    "alias3x": {"help": "aliased python3.x.exe entry-point binaries"},
}


PRESETS = {
    "appx": {
        "help": "APPX package",
        "options": [
            "stable",
            "pip",
            "tcltk",
            "idle",
            "venv",
            "dev",
            "launchers",
            "appxmanifest",
            "alias",
            "alias3x",
            # XXX: Disabled for now "precompile",
        ],
    },
    "nuget": {
        "help": "nuget package",
        "options": [
            "dev",
            "pip",
            "stable",
            "venv",
            "props",
            "nuspec",
            "alias",
        ],
    },
    "iot": {"help": "Windows IoT Core", "options": ["alias", "stable", "pip"]},
    "default": {
        "help": "development kit package",
        "options": [
            "stable",
            "pip",
            "tcltk",
            "idle",
            "tests",
            "venv",
            "dev",
            "symbols",
            "html-doc",
            "alias",
        ],
    },
    "embed": {
        "help": "embeddable package",
        "options": [
            "alias",
            "stable",
            "zip-lib",
            "flat-dlls",
            "underpth",
            "precompile",
        ],
    },
}


@public
def get_argparse_options():
    for opt, info in OPTIONS.items():
        help = "When specified, includes {}".format(info["help"])
        if info.get("not-in-all"):
            help = "{}. Not affected by --include-all".format(help)

        yield "--include-{}".format(opt), help

    for opt, info in PRESETS.items():
        help = "When specified, includes default options for {}".format(info["help"])
        yield "--preset-{}".format(opt), help


def ns_get(ns, key, default=False):
    return getattr(ns, key.replace("-", "_"), default)


def ns_set(ns, key, value=True):
    k1 = key.replace("-", "_")
    k2 = "include_{}".format(k1)
    if hasattr(ns, k2):
        setattr(ns, k2, value)
    elif hasattr(ns, k1):
        setattr(ns, k1, value)
    else:
        raise AttributeError("no argument named '{}'".format(k1))


@public
def update_presets(ns):
    for preset, info in PRESETS.items():
        if ns_get(ns, "preset-{}".format(preset)):
            for opt in info["options"]:
                ns_set(ns, opt)

    if ns.include_all:
        for opt in OPTIONS:
            if OPTIONS[opt].get("not-in-all"):
                continue
      name: "Build and Test For PR"

on: [push, pull_request, workflow_dispatch]

permissions:
  contents: read

env:
  FORK_COUNT: 2
  FAIL_FAST: 0
  SHOW_ERROR_DETAIL: 1
  VERSIONS_LIMIT: 4
  JACOCO_ENABLE: true
  CANDIDATE_VERSIONS: '
    spring.version:5.3.24,6.1.5;
    spring-boot.version:2.7.6,3.2.3;
    '
  MAVEN_OPTS: >-
    -XX:+UseG1GC
    -XX:InitiatingHeapOccupancyPercent=45
    -XX:+UseStringDeduplication
    -XX:-TieredCompilation
    -XX:TieredStopAtLevel=1
    -Dmaven.javadoc.skip=true
    -Dmaven.wagon.http.retryHandler.count=5
    -Dmaven.wagon.httpconnectionManager.ttlSeconds=120
  MAVEN_ARGS: >-
    -e
    --batch-mode
    --no-snapshot-updates
    --no-transfer-progress
    --fail-fast

jobs:
  # 1. Comprobación de formato de código
  check-format:
    name: "Check if code needs formatting"
    runs-on: ubuntu-22.04
    steps:
      - name: "Checkout"
        uses: actions/checkout@v4
      - name: "Setup maven"
        uses: actions/setup-java@v4
        with:
          java-version: 21
          distribution: zulu
      - name: "Check if code aligns with code style"
        id: check
        run: mvn --log-file mvn.log spotless:check
        continue-on-error: true
      - name: "Upload checkstyle result"
        uses: actions/upload-artifact@v4
        with:
          name: checkstyle-result
          path: mvn.log
      - name: "Generate Summary for successful run"
        if: ${{ steps.check.outcome == 'success' }}
        run: |
          echo ":ballot_box_with_check: Kudos! No formatting issues found!" >> $GITHUB_STEP_SUMMARY
      - name: "Generate Summary for failed run"
        if: ${{ steps.check.outcome == 'failure' }}
        run: |
          echo "## :negative_squared_cross_mark: Formatting issues found!" >> $GITHUB_STEP_SUMMARY
          echo "\`\`\`" >> $GITHUB_STEP_SUMMARY
          cat mvn.log | grep "ERROR" | sed 's/Check if code needs formatting    Check if code aligns with code style   [0-9A-Z:.-]\+//' | sed 's/\[ERROR] //' | head -n -11 >> $GITHUB_STEP_SUMMARY
          echo "\`\`\`" >> $GITHUB_STEP_SUMMARY
          echo "Please run \`mvn spotless:apply\` to fix the formatting issues." >> $GITHUB_STEP_SUMMARY
      - name: "Fail if code needs formatting"
        if: ${{ steps.check.outcome == 'failure' }}
        uses: actions/github-script@v7.0.1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          script: |
            core.setFailed("Formatting issues found! \nRun \`mvn spotless:apply\` to fix.")

  # 2. Comprobación de licencias
  license:
    name: "Check License"
    needs: check-format
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
      - name: "Check License"
        uses: apache/skywalking-eyes@e1a02359b239bd28de3f6d35fdc870250fa513d5
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      - name: "Set up JDK 21"
        uses: actions/setup-java@v4
        with:
          distribution: 'zulu'
          java-version: 21
      - name: "Compile Dubbo (Linux)"
        run: |
          ./mvnw ${{ env.MAVEN_ARGS }} -T 2C clean install -Pskip-spotless -Dmaven.test.skip=true -Dcheckstyle.skip=true -Dcheckstyle_unix.skip=true -Drat.skip=true
      - name: "Check Dependencies' License"
        uses: apache/skywalking-eyes/dependency@e1a02359b239bd28de3f6d35fdc870250fa513d5
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          config: .licenserc.yaml
          mode: check

  # 3. Construcción de fuente
  build-source:
    name: "Build Dubbo"
    needs: check-format
    runs-on: ubuntu-22.04
    outputs:
      version: ${{ steps.dubbo-version.outputs.version }}
    steps:
      - name: "Checkout code"
        uses: actions/checkout@v4
      - name: "Set up JDK"
        uses: actions/setup-java@v4
        with:
          distribution: 'zulu'
          java-version: 21
      - name: "Set current date as env variable"
        run: echo "TODAY=$(date +'%Y%m%d')" >> $GITHUB_ENV
      - name: "Restore local maven repository cache"
        uses: actions/cache/restore@v4
        id: cache-maven-repository
        with:
          path: ~/.m2/repository
          key: ${{ runner.os }}-maven-${{ hashFiles('**/pom.xml') }}-${{ env.TODAY }}
      - name: "Restore common local maven repository cache"
        uses: actions/cache/restore@v4
        if: steps.cache-maven-repository.outputs.cache-hit != 'true'
        with:
          path: ~/.m2/repository
          key: ${{ runner.os }}-maven-${{ hashFiles('**/pom.xml') }}
          restore-keys: |
            ${{ runner.os }}-maven-
      - name: "Clean dubbo cache"
        run: rm -rf ~/.m2/repository/org/apache/dubbo
      - name: "Build Dubbo with maven"
        run: |
          ./mvnw ${{ env.MAVEN_ARGS }} clean install -Psources,skip-spotless,checkstyle -Dmaven.test.skip=true -DembeddedZookeeperPath=${{ github.workspace }}/.tmp/zookeeper
      - name: "Save dubbo cache"
        uses: actions/cache/save@v4
        with:
          path: ~/.m2/repository/org/apache/dubbo
          key: ${{ runner.os }}-dubbo-snapshot-${{ github.sha }}-${{ github.run_id }}
      - name: "Clean dubbo cache"
        run: rm -rf ~/.m2/repository/org/apache/dubbo
      - name: "Save local maven repository cache"
        uses: actions/cache/save@v4
        if: steps.cache-maven-repository.outputs.cache-hit != 'true'
        with:
          path: ~/.m2/repository
          key: ${{ runner.os }}-maven-${{ hashFiles('**/pom.xml') }}-${{ env.TODAY }}
      - name: "Pack class result"
        run: |
          shopt -s globstar
          zip ${{ github.workspace }}/class.zip **/target/classes/* -r
      - name: "Upload class result"
        uses: actions/upload-artifact@v4
        with:
          name: "class-file"
          path: ${{ github.workspace }}/class.zip
      - name: "Pack checkstyle file if failure"
        if: failure()
        run: zip ${{ github.workspace }}/checkstyle.zip *checkstyle* -r
      - name: "Upload checkstyle file if failure"
        uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: "checkstyle-file"
          path: ${{ github.workspace }}/checkstyle.zip
      - name: "Calculate Dubbo Version"
        id: dubbo-version
        run: |
          REVISION=`awk '/<revision>[^<]+<\/revision>/{gsub(/<revision>|<\/revision>/,"",$1);print $1;exit;}' ./pom.xml`
          echo "version=$REVISION" >> $GITHUB_OUTPUT
          echo "dubbo version: $REVISION"

  # 4. Preparación para pruebas unitarias
  unit-test-prepare:
    name: "Preparation for Unit Test"
    needs: check-format
    runs-on: ubuntu-22.04
    strategy:
      fail-fast: false
    env:
      ZOOKEEPER_VERSION: 3.7.2
    steps:
      - name: "Cache zookeeper binary archive"
        uses: actions/cache@v3
        id: "cache-zookeeper"
        with:
          path: ${{ github.workspace }}/.tmp/zookeeper
          key: zookeeper-${{ runner.os }}-${{ env.ZOOKEEPER_VERSION }}
          restore-keys: |
            zookeeper-${{ runner.os }}-${{ env.ZOOKEEPER_VERSION }}
      - name: "Set up msys2 if necessary"
        uses: msys2/setup-msys2@v2
        if: ${{ startsWith( matrix.os, 'windows') && steps.cache-zookeeper.outputs.cache-hit != 'true' }}
        with:
          release: false
      - name: "Download zookeeper binary archive in Linux OS"
        run: |
          mkdir -p ${{ github.workspace }}/.tmp/zookeeper
          wget -t 1 -T 120 -c https://archive.apache.org/dist/zookeeper/zookeeper-${{ env.ZOOKEEPER_VERSION }}/apache-zookeeper-${{ env.ZOOKEEPER_VERSION }}-bin.tar.gz -O ${{ github.workspace }}/.tmp/zookeeper/apache-zookeeper-bin.tar.gz ||
          wget -t 1 -T 120 -c https://apache.website-solution.net/zookeeper/zookeeper-${{ env.ZOOKEEPER_VERSION }}/apache-zookeeper-${{ env.ZOOKEEPER_VERSION }}-bin.tar.gz -O ${{ github.workspace }}/.tmp/zookeeper/apache-zookeeper-bin.tar.gz ||
          wget -t 1 -T 120 -c http://ftp.jaist.ac.jp/pub/apache/zookeeper/zookeeper-${{ env.ZOOKEEPER_VERSION }}/apache-zookeeper-${{ env.ZOOKEEPER_VERSION }}-bin.tar.gz -O ${{ github.workspace }}/.tmp/zookeeper/apache-zookeeper-bin.tar.gz ||
          wget -t 1 -T 120 -c http://apache.mirror.cdnetworks.com/zookeeper/zookeeper-${{ env.ZOOKEEPER_VERSION }}/apache-zookeeper-${{ env.ZOOKEEPER_VERSION }}-bin.tar.gz -O ${{ github.workspace }}/.tmp/zookeeper/apache-zookeeper-bin.tar.gz ||
          wget -t 1 -T 120 -c http://mirror.apache-kr.org/apache/zookeeper/zookeeper-${{ env.ZOOKEEPER_VERSION }}/apache-zookeeper-${{ env.ZOOKEEPER_VERSION }}-bin.tar.gz -O ${{ github.workspace }}/.tmp/zookeeper/apache-zookeeper-bin.tar.gz
          echo "list the downloaded zookeeper binary archive"
          ls -al ${{ github.workspace }}/.tmp/zookeeper/apache-zookeeper-bin.tar.gz

  # 5. Pruebas unitarias
  unit-test:
    needs: [check-format, unit-test-prepare]
    name: "Unit Test On ubuntu-22.04 Java: ${{ matrix.java }}"
    runs-on: ubuntu-22.04
    strategy:
      fail-fast: false
      matrix:
        java: [ 8, 11, 17, 21, 25 ]
    env:
      DISABLE_FILE_SYSTEM_TEST: true
      CURRENT_ROLE: ${{ matrix.case-role }}
      ZOOKEEPER_VERSION: 3.7.2
    steps:
      - name: "Set MAVEN_OPTS for JDK 24+"
        if: ${{ matrix.java >= 24 }}
        run: echo "MAVEN_OPTS=--sun-misc-unsafe-memory-access=allow" >> $GITHUB_ENV
      - name: "Checkout code"
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: "Set up JDK ${{ matrix.java }}"
        uses: actions/setup-java@v4
        with:
          distribution: 'zulu'
          java-version: ${{ matrix.java }}
      - name: "Set current date as env variable"
        run: echo "TODAY=$(date +'%Y%m%d')" >> $GITHUB_ENV
      - name: "Cache local maven repository"
        uses: actions/cache/restore@v4
        with:
          path: ~/.m2/repository
          key: ${{ runner.os }}-maven-${{ hashFiles('**/pom.xml') }}-${{ env.TODAY }}
          restore-keys: |
            ${{ runner.os }}-maven-${{ hashFiles('**/pom.xml') }}
            ${{ runner.os }}-maven-
      - name: "Cache zookeeper binary archive"
        uses: actions/cache@v3
        id: "cache-zookeeper"
        with:
          path: ${{ github.workspace }}/.tmp/zookeeper
          key: zookeeper-${{ runner.os }}-${{ env.ZOOKEEPER_VERSION }}
          restore-keys: |
            zookeeper-${{ runner.os }}-
      - name: "Test with maven on Java: 8"
        timeout-minutes: 90
        if: ${{ matrix.java == '8' }}
        run: |
          set -o pipefail
          ./mvnw ${{ env.MAVEN_ARGS }} clean test verify -Pjacoco,'!jdk15ge-add-open',skip-spotless -DtrimStackTrace=false -Dmaven.test.skip=false -Dcheckstyle.skip=false -Dcheckstyle_unix.skip=false -Drat.skip=false -DembeddedZookeeperPath=${{ github.workspace }}/.tmp/zookeeper 2>&1 | tee >(grep -n -B 1 -A 200 "FAILURE! -- in" > test_errors.log)
      - name: "Test with maven on Java: ${{ matrix.java }}"
        timeout-minutes: 90
        if: ${{ matrix.java != '8' }}
        run: |
          set -o pipefail
          ./mvnw ${{ env.MAVEN_ARGS }} clean test verify -Pjacoco,jdk15ge-simple,'!jdk15ge-add-open',skip-spotless -DtrimStackTrace=false -Dmaven.test.skip=false -Dcheckstyle.skip=false -Dcheckstyle_unix.skip=false -Drat.skip=false -DembeddedZookeeperPath=${{ github.workspace }}/.tmp/zookeeper 2>&1 | tee >(grep -n -B 1 -A 200 "FAILURE! -- in" > test_errors.log)
      - name: "Print test error log"
        if: failure()
        run: cat test_errors.log
      - name: "Upload coverage to Codecov"
        uses: codecov/codecov-action@v5
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          verbose: true
          flags: unit-tests-java${{ matrix.java }}
        env:
          CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}
      - name: "Upload surefire reports"
        uses: actions/upload-artifact@v4
        with:
          name: surefire-reports-java${{ matrix.java }}
          path: "**/target/surefire-reports/**"

  # 6. Preparación para pruebas de ejemplos
  samples-test-prepare:
    needs: check-format
    runs-on: ubuntu-22.04
    env:
      JOB_COUNT: 3
    steps:
      - uses: actions/checkout@v4
        with:
          repository: 'apache/dubbo-samples'
          ref: master
      - name: "Prepare test list"
        run: bash ./test/scripts/prepare-test.sh
      - name: "Upload test list"
        uses: actions/upload-artifact@v4
        with:
          name: samples-test-list
          path: test/jobs

  # 7. Ejecución de pruebas de ejemplos
  samples-test-job:
    needs: [check-format, build-source, samples-test-prepare]
    name: "Samples
      ns_set(ns, opt)
