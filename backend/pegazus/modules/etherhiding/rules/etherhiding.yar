rule EtherHiding_Implant_Marker_A8 : critical
{
    meta:
        description = "Marcador literal de implante conocido (variante RESTOBAR/AVA/RETAIL/XINERGIAPRO): global.i=\"A8-...\"."
    strings:
        $marker = "global.i=\"A8-"
    condition:
        $marker
}

rule EtherHiding_Implant_Marker_Bang : critical
{
    meta:
        description = "Marcador literal de implante conocido (variante Restaurante): global['!']='...'."
    strings:
        $marker = "global['!']='"
    condition:
        $marker
}

rule EtherHiding_Implant_Marker_AppEval : critical
{
    meta:
        description = "Marcador literal de implante conocido, con nombre de app embebido: global['e']='app-<nombre>-eval'."
    strings:
        $marker = /global\['e'\]='app-[a-zA-Z0-9_.-]+-eval'/
    condition:
        $marker
}

rule EtherHiding_Obfuscated_Identifier_Markers : critical
{
    meta:
        description = "Identificadores especificos de variantes de este implante vistas en incidentes reales (funcion ofuscada '_$_1e42', identificador 'q4FZkxX', archivo de salida 'main.inz.cjs')."
    strings:
        $var1 = "_$_1e42"
        $var2 = "q4FZkxX"
        $file1 = "main.inz.cjs"
    condition:
        any of them
}

rule EtherHiding_Hidden_Node_Spawn : high
{
    meta:
        description = "Ejecucion de un proceso node oculto y desacoplado del padre (windowsHide + detached + spawn de 'node' con '-e')."
    strings:
        $hide = "windowsHide" nocase
        $detached = "detached" nocase
        $spawn = "spawn(" nocase
        $node1 = "'node'"
        $node2 = "\"node\""
        $flag1 = "'-e'"
        $flag2 = "\"-e\""
    condition:
        $hide and $detached and $spawn and (1 of ($node*)) and (1 of ($flag*))
}

rule EtherHiding_Blockchain_RPC_Reference : medium
{
    meta:
        description = "Referencia a proveedores publicos de RPC de Ethereum, usados como mecanismo de resolucion de C2 en campanas EtherHiding. No es malicioso por si solo: revisar si el proyecto tiene relacion legitima con crypto/web3."
    strings:
        $env = "ETH_RPC_URL"
        $d1 = "1rpc.io" nocase
        $d2 = "drpc.org" nocase
        $d3 = "publicnode.com" nocase
        $d4 = "blockscout.com" nocase
        $d5 = "blastapi.io" nocase
    condition:
        any of them
}

rule EtherHiding_CreateRequire_Scaffold : info
{
    meta:
        description = "createRequire(import.meta.url) en un archivo de configuracion de build. No es malicioso por si solo: es scaffolding legitimo de ESM. Solo es relevante si aparece de forma nueva/inesperada -- correlacionar con 'git log -G' sobre este archivo para ver cuando se introdujo."
    strings:
        $marker = "createRequire(import.meta.url)"
    condition:
        $marker
}
