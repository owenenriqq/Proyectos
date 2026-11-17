# Verificar si se ejecuta como administrador
$currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell "-ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$folder = "C:\Program Files (x86)\Sol Sistemas"

# Obtener el grupo 'Users' por SID
$usersSID = New-Object System.Security.Principal.SecurityIdentifier("S-1-5-32-545")
$group = $usersSID.Translate([System.Security.Principal.NTAccount]).Value

# Obtener ACL actual
$acl = Get-Acl $folder

# Crear nueva regla
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $group,
    "FullControl",
    "ContainerInherit, ObjectInherit",
    "None",
    "Allow"
)

# Limpiar reglas previas de ese grupo
$acl.Access | Where-Object { $_.IdentityReference -eq $group } | ForEach-Object {
    $acl.RemoveAccessRule($_) | Out-Null
}

# Agregar nueva regla
$acl.AddAccessRule($rule) | Out-Null

# Aplicar cambios
Set-Acl -Path $folder -AclObject $acl

# Mensaje final
Write-Host "[OK] Permisos aplicados correctamente a '$group'." -ForegroundColor Green

# Cuenta regresiva
for ($i = 5; $i -ge 1; $i--) {
    Write-Host -NoNewline "`rCerrando en $i segundos... "
    Start-Sleep -Seconds 1
}

# Fin
Write-Host "`nProceso finalizado."
Stop-Process -Id $PID
