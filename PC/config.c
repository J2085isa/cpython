/* Module configuration */

/* This file contains the table of built-in modules.
    See create_builtin() in import.c. */

#include "Python.h"
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

extern PyObject* PyInit__abc(void);
extern PyObject* PyInit_array(void);
extern PyObject* PyInit_binascii(void);
extern PyObject* PyInit_cmath(void);
extern PyObject* PyInit_errno(void);
extern PyObject* PyInit_faulthandler(void);
extern PyObject* PyInit__tracemalloc(void);
extern PyObject* PyInit_gc(void);
extern PyObject* PyInit_math(void);
extern PyObject* PyInit__md5(void);
extern PyObject* PyInit_nt(void);
extern PyObject* PyInit__operator(void);
extern PyObject* PyInit__signal(void);
extern PyObject* PyInit__sha1(void);
extern PyObject* PyInit__sha2(void);
extern PyObject* PyInit__sha3(void);
extern PyObject* PyInit__statistics(void);
extern PyObject* PyInit__sysconfig(void);
extern PyObject* PyInit__typing(void);
extern PyObject* PyInit__blake2(void);
extern PyObject* PyInit_time(void);
extern PyObject* PyInit__thread(void);
#ifdef WIN32
extern PyObject* PyInit_msvcrt(void);
extern PyObject* PyInit__locale(void);
#endif
extern PyObject* PyInit__codecs(void);
extern PyObject* PyInit__weakref(void);
/* XXX: These two should really be extracted to standalone extensions. */
extern PyObject* PyInit_xxsubtype(void);
extern PyObject* PyInit__interpreters(void);
extern PyObject* PyInit__interpchannels(void);
extern PyObject* PyInit__interpqueues(void);
extern PyObject* PyInit__random(void);
extern PyObject* PyInit_itertools(void);
extern PyObject* PyInit__collections(void);
extern PyObject* PyInit__heapq(void);
extern PyObject* PyInit__bisect(void);
extern PyObject* PyInit__symtable(void);
extern PyObject* PyInit_mmap(void);
extern PyObject* PyInit__csv(void);
extern PyObject* PyInit__sre(void);
#if defined(MS_WINDOWS_DESKTOP) || defined(MS_WINDOWS_SYSTEM) || defined(MS_WINDOWS_GAMES)
extern PyObject* PyInit_winreg(void);
#endif
extern PyObject* PyInit__struct(void);
extern PyObject* PyInit__datetime(void);
extern PyObject* PyInit__functools(void);
extern PyObject* PyInit__json(void);
#ifdef _Py_HAVE_ZLIB
extern PyObject* PyInit_zlib(void);
#endif

extern PyObject* PyInit__multibytecodec(void);
extern PyObject* PyInit__codecs_cn(void);
extern PyObject* PyInit__codecs_hk(void);
extern PyObject* PyInit__codecs_iso2022(void);
extern PyObject* PyInit__codecs_jp(void);
extern PyObject* PyInit__codecs_kr(void);
extern PyObject* PyInit__codecs_tw(void);
extern PyObject* PyInit__winapi(void);
extern PyObject* PyInit__lsprof(void);
extern PyObject* PyInit__ast(void);
extern PyObject* PyInit__io(void);
extern PyObject* PyInit__pickle(void);
extern PyObject* PyInit_atexit(void);
extern PyObject* _PyWarnings_Init(void);
extern PyObject* PyInit__string(void);
extern PyObject* PyInit__stat(void);
extern PyObject* PyInit__opcode(void);
extern PyObject* PyInit__contextvars(void);
extern PyObject* PyInit__tokenize(void);

/* tools/freeze/makeconfig.py marker for additional "extern" */
/* -- ADDMODULE MARKER 1 -- */

extern PyObject* PyMarshal_Init(void);
extern PyObject* PyInit__imp(void);

struct _inittab _PyImport_Inittab[] = {
    {"_abc", PyInit__abc},
    {"array", PyInit_array},
    {"_ast", PyInit__ast},
    {"binascii", PyInit_binascii},
    {"cmath", PyInit_cmath},
    {"errno", PyInit_errno},
    {"faulthandler", PyInit_faulthandler},
    {"gc", PyInit_gc},
    {"math", PyInit_math},
    {"nt", PyInit_nt}, /* Use the NT os functions, not posix */
    {"_operator", PyInit__operator},
    {"_signal", PyInit__signal},
    {"_md5", PyInit__md5},
    {"_sha1", PyInit__sha1},
    {"_sha2", PyInit__sha2},
    {"_sha3", PyInit__sha3},
    {"_blake2", PyInit__blake2},
    {"_sysconfig", PyInit__sysconfig},
    {"time", PyInit_time},
    {"_thread", PyInit__thread},
    {"_tokenize", PyInit__tokenize},
    {"_typing", PyInit__typing},
    {"_statistics", PyInit__statistics},
#ifdef WIN32
    {"msvcrt", PyInit_msvcrt},
    {"_locale", PyInit__locale},
#endif
    {"_tracemalloc", PyInit__tracemalloc},
    /* XXX Should _winapi go in a WIN32 block?  not WIN64? */
    {"_winapi", PyInit__winapi},

    {"_codecs", PyInit__codecs},
    {"_weakref", PyInit__weakref},
    {"_random", PyInit__random},
    {"_bisect", PyInit__bisect},
    {"_heapq", PyInit__heapq},
    {"_lsprof", PyInit__lsprof},
    {"itertools", PyInit_itertools},
    {"_collections", PyInit__collections},
    {"_symtable", PyInit__symtable},
#if defined(MS_WINDOWS_DESKTOP) || defined(MS_WINDOWS_GAMES)
    {"mmap", PyInit_mmap},
#endif
    {"_csv", PyInit__csv},
    {"_sre", PyInit__sre},
#if defined(MS_WINDOWS_DESKTOP) || defined(MS_WINDOWS_SYSTEM) || defined(MS_WINDOWS_GAMES)
    {"winreg", PyInit_winreg},
#endif
    {"_struct", PyInit__struct},
    {"_datetime", PyInit__datetime},
    {"_functools", PyInit__functools},
    {"_json", PyInit__json},

    {"xxsubtype", PyInit_xxsubtype},
    {"_interpreters", PyInit__interpreters},
    {"_interpchannels", PyInit__interpchannels},
    {"_interpqueues", PyInit__interpqueues},
#ifdef _Py_HAVE_ZLIB
    {"zlib", PyInit_zlib},
#endif

    /* CJK codecs */
    {"_multibytecodec", PyInit__multibytecodec},
    {"_codecs_cn", PyInit__codecs_cn},
    {"_codecs_hk", PyInit__codecs_hk},
    {"_codecs_iso2022", PyInit__codecs_iso2022},
    {"_codecs_jp", PyInit__codecs_jp},
    {"_codecs_kr", PyInit__codecs_kr},
    {"_codecs_tw", PyInit__codecs_tw},

/* tools/freeze/makeconfig.py marker for additional "_inittab" entries */
/* -- ADDMODULE MARKER 2 -- */

    /* This module "lives in" with marshal.c */
    {"marshal", PyMarshal_Init},

    /* This lives it with import.c */
    {"_imp", PyInit__imp},

    /* These entries are here for sys.builtin_module_names */
    {"builtins", NULL},
    {"sys", NULL},
    {"_warnings", _PyWarnings_Init},
    {"_string", PyInit__string},

    {"_io", PyInit__io},
    {"_pickle", PyInit__pickle},
    {"atexit", PyInit_atexit},
    {"_stat", PyInit__stat},
    {"_opcode", PyInit__opcode},

    {"_contextvars", PyInit__contextvars},

    /* Sentinel */
    {0, 0}
};
