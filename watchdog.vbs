' Silent wrapper for watchdog.cmd.
' Runs watchdog.cmd with window style 0 (hidden) so no console flashes.
' Uses the same path-resolution pattern as start.vbs.

Option Explicit

Dim fso, shell, here, cmd
Set fso   = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

here = fso.GetParentFolderName(WScript.ScriptFullName)
cmd  = "cmd.exe /c """ & here & "\watchdog.cmd"""

' Window style 0 = hidden. False = do not wait.
shell.Run cmd, 0, False
