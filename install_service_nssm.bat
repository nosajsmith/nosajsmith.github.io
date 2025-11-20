set SVC=MWE_Bridge
set EXE="C:\Program Files\Python313\python.exe"
set SCRIPTPATH="%~dp0server\mwe_bridge_allinone_p6.py"
set WORKDIR="%~dp0server"
nssm install %%SVC%% %%EXE%% %%SCRIPTPATH%%
nssm set %%SVC%% AppDirectory %%WORKDIR%%
nssm set %%SVC%% AppStdout "%~dp0logs\service_stdout.log"
nssm set %%SVC%% AppStderr "%~dp0logs\service_stderr.log"
nssm set %%SVC%% Start SERVICE_AUTO_START
nssm start %%SVC%%
sc query %%SVC%%
