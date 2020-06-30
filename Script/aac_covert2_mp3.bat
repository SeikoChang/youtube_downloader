@ECHO ON
@ECHO.

SETLOCAL ENABLEDELAYEDEXPANSION

SET CURRDIR=%~dp0
SET ext=mp3
SET "FFMPEG_EXE=%~dp0..\ffmpeg-latest-win64-static\bin\ffmpeg.exe"
SET "YOUTUBE=%~dp0..\Youtube"

FOR /F "delims==" %%G IN ('DIR %YOUTUBE% /A:A /S /B /N') DO (
   (@ECHO "%%G" | FIND /I ".mp3 .srt" >NUL 1>&2) || (
      SET CCMD="%FFMPEG_EXE%" -i "%%G" -vn -ar 44100 -ac 2 -b:a 192k "%%~pG%%~nG.%ext%" -n
   	  @(ECHO !CCMD!) >>job.log
      @!CCMD! >> debug.log 2>&1
   )
)

@IF %ErrorLevel% NEQ 0 @EXIT /B %ErrorLevel%
@GOTO :END

:END
@SET CURRDIR=
@SET ext=
@SET FFMPEG_EXE=
@SET YOUTUBE=
@SET CCMD=
