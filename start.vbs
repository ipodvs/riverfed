' Youtuber background launcher.
'
' Double-click this file to start the server *detached* (no terminal
' window) and open the web UI in your default browser. The server writes
' to server.log in this folder. Use stop.cmd to shut it down.

Option Explicit

Dim fso, shell, here, pyw, py, server, browserUrl
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

here = fso.GetParentFolderName(WScript.ScriptFullName)
pyw  = here & "\.venv\Scripts\pythonw.exe"
py   = here & "\.venv\Scripts\python.exe"
server = here & "\server.py"
browserUrl = "http://127.0.0.1:8765/"

If Not fso.FileExists(server) Then
    MsgBox "server.py not found in:" & vbCrLf & here, vbCritical, "Youtuber"
    WScript.Quit 1
End If

Dim cmd
If fso.FileExists(pyw) Then
    cmd = """" & pyw & """ """ & server & """"
ElseIf fso.FileExists(py) Then
    cmd = """" & py & """ """ & server & """"
Else
    MsgBox "No Python found in .venv. Run setup first (see README).", vbCritical, "Youtuber"
    WScript.Quit 1
End If

' Run mode 0 = hidden window, False = do not wait.
shell.Run cmd, 0, False

' Give the server ~1.5s to bind to the port, then open the browser.
WScript.Sleep 1500
shell.Run browserUrl, 1, False
