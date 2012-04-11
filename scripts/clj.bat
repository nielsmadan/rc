:: Setup:
:: 
:: 1. Change the constants to match your paths
:: 2. Put this clj.bat file on your PATH
::
:: Usage:
::
:: clj                           # Starts REPL
:: clj my_script.clj             # Runs the script
:: clj my_script.clj arg1 arg2   # Runs the script with arguments

@echo off

:: Change the following to match your paths
set CLOJURE_DIR=C:\usr\bin\clojure
set CLOJURE_JAR=%CLOJURE_DIR%\clojure-1.3.0.jar

if [%1] == [] goto noargs
goto :someargs

:noargs
java -cp .;%CLOJURE_JAR% clojure.main
goto end

:someargs
java -cp .;%CLOJURE_JAR% clojure.main %1 -- %*

:end
