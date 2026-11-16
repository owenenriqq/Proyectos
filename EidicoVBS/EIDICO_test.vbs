SET sh = CreateObject("Wscript.Shell")
SET fs = CreateObject("Scripting.FileSystemObject")

cFileName      = "EidicoPrueba.Exe"
cLocalFolder   = "C:\Program Files (x86)\Sol Sistemas\Eidico\"
cServerFolder  = "\\172.31.11.146\Fileserver\EidicoPrueba\"
localFilePath  = cLocalFolder & cFileName
serverFilePath = cServerFolder & cFileName

' Verificar que el ejecutable exista en el servidor
If Not fs.FileExists(serverFilePath) Then
    MsgBox "Eidico no encontrado."
    WScript.Quit
End If

serverFileSize = fs.GetFile(serverFilePath).Size

' Si no existe localmente, copiar todos los archivos desde el servidor
If Not fs.FileExists(localFilePath) Then
    MsgBox "Copiando Eidico.  Pulse Aceptar y espere el siguiente mensaje." & vbNewLine & vbNewLine & "                             (puede demorar unos minutos)"
    CopiarArchivos cServerFolder, cLocalFolder, "Error copiando Eidico"
    MsgBox "Eidico se copio correctamente.  Aceptar para continuar."
Else
    ' Si ya existe, actualizar solo si difiere el tamano o la version del servidor es mayor
    localSize      = fs.GetFile(localFilePath).Size
    cVersionLocal  = fs.GetFileVersion(localFilePath)
    cVersionServer = fs.GetFileVersion(serverFilePath)

    If True Then
        CerrarSiEstaAbierto cFileName
        MsgBox "Actualizando Eidico.  Pulse Aceptar y espere el siguiente mensaje." & vbNewLine & vbNewLine & "                         (puede demorar unos minutos)"
        CopiarArchivos cServerFolder, cLocalFolder, "Error actualizando Eidico"
        MsgBox "Eidico se actualizo correctamente.  Aceptar para continuar."
    End If
End If

' Verificar integridad por tamano antes de ejecutar
If fs.FileExists(localFilePath) Then
    If fs.GetFile(localFilePath).Size <> serverFileSize Then
        MsgBox "Eidico incompleto. No se puede ejecutar."
        WScript.Quit
    End If
    sh.Run """" & localFilePath & """", 1
End If

' Copia los archivos del servidor a la carpeta local manejando errores
Sub CopiarArchivos(origen, destino, mensajeError)
    On Error Resume Next
    fs.CopyFile origen & "*.*", destino, True
    If Err.Number <> 0 Then
        MsgBox mensajeError & ": " & Err.Description
        WScript.Quit
    End If
    On Error GoTo 0
End Sub

' Compara dos versiones con formato "a.b.c.d" de forma numerica
Function VersionMenorQue(verLocal, verServer)
    Dim arrLocal, arrServer, maxLen, i, numLocal, numServer
    arrLocal  = Split(verLocal, ".")
    arrServer = Split(verServer, ".")

    If UBound(arrLocal) > UBound(arrServer) Then
        maxLen = UBound(arrLocal)
    Else
        maxLen = UBound(arrServer)
    End If

    For i = 0 To maxLen
        numLocal = 0
        numServer = 0
        If i <= UBound(arrLocal) Then
            If IsNumeric(arrLocal(i)) Then numLocal = CLng(arrLocal(i))
        End If
        If i <= UBound(arrServer) Then
            If IsNumeric(arrServer(i)) Then numServer = CLng(arrServer(i))
        End If

        If numLocal < numServer Then
            VersionMenorQue = True
            Exit Function
        ElseIf numLocal > numServer Then
            VersionMenorQue = False
            Exit Function
        End If
    Next

    VersionMenorQue = False
End Function

' Verifica si el proceso esta abierto y ofrece cerrarlo antes de actualizar
Sub CerrarSiEstaAbierto(nombreProceso)
    Dim wmi, procesos, resp
    Set wmi = GetObject("winmgmts:\\.\root\cimv2")
    Set procesos = wmi.ExecQuery("Select * from Win32_Process Where Name = '" & nombreProceso & "'")

    If procesos.Count > 0 Then
        resp = MsgBox("Hay una actualizacion disponible para Eidico." & vbNewLine & vbNewLine & "Para continuar se cerraran las ventanas abiertas del sistema. Asegurese de guardar sus cambios antes de continuar." & vbNewLine & vbNewLine & "Desea cerrar y actualizar ahora?", vbYesNo)
        If resp = vbYes Then
            sh.Run "taskkill /F /IM " & nombreProceso, 0, True
            WScript.Sleep 1000
        Else
            WScript.Quit
        End If
    End If
End Sub