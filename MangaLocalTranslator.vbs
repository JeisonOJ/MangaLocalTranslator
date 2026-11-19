Option Explicit
Dim fs, shell, root, python, entry
Set fs = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
root = fs.GetParentFolderName(WScript.ScriptFullName)
python = fs.BuildPath(root, "evaluation\envs\crf312\pythonw.exe")
entry = fs.BuildPath(root, "desktop\launch.pyw")
If Not fs.FileExists(python) Or Not fs.FileExists(entry) Then
    MsgBox "The project-local Python runtime or application entry point is missing.", 16, "MangaLocalTranslator"
    WScript.Quit 1
End If
shell.CurrentDirectory = root
' pythonw suppresses the console. Normal window style allows Qt to show its GUI.
On Error Resume Next
shell.Run Chr(34) & python & Chr(34) & " -B " & Chr(34) & entry & Chr(34), 1, False
If Err.Number <> 0 Then
    MsgBox "Could not start MangaLocalTranslator. Windows error " & Err.Number & ". Check the project-local Python executable and application paths.", 16, "MangaLocalTranslator"
    WScript.Quit 1
End If
On Error GoTo 0
