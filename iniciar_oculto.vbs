Set shell = CreateObject("WScript.Shell")
Set sistemaArquivos = CreateObject("Scripting.FileSystemObject")
pasta = sistemaArquivos.GetParentFolderName(WScript.ScriptFullName)
bat = sistemaArquivos.BuildPath(pasta, "iniciar_sistema.bat")
comando = "cmd.exe /c """ & bat & """"
shell.Run comando, 0, False
