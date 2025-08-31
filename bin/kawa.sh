#!/bin/sh
thisfile=`which $0`
thisdir=`dirname $thisfile`
if test -f $thisdir/../kawa-1.11-ai2.jar
then KAWALIB=${KAWALIB-$thisdir/../kawa-1.11-ai2.jar}
else KAWALIB=${KAWALIB-/tmp/kawa-install/share/java/kawa-1.11-ai2.jar}; fi
CLASSPATH=${KAWALIB}:${CLASSPATH-}
export CLASSPATH
exec ${JAVA-/usr/bin/java} kawa.repl "$@"
