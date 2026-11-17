Set shell = CreateObject("Shell.Application")
Set fso = CreateObject("Scripting.FileSystemObject")

remoteBat = "\\172.30.0.13\it\CMD\IT_Scripts\EzSetup.bat"

localBat = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "EzSetup.bat")

If fso.FileExists(localBat) Then
    shell.ShellExecute localBat, "", "", "runas", 1
ElseIf fso.FileExists(remoteBat) Then
    shell.ShellExecute remoteBat, "", "", "runas", 1
Else
    MsgBox "No se encuentra el archivo EasySetup.bat", vbCritical, "Error"
End If

