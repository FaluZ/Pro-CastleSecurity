export interface JsFinding {
  title: string;
  description: string;
  severity: "info" | "low" | "medium" | "high" | "critical";
  filePath: string;
  evidence?: string;
}

/**
 * Scaffold sin logica real todavia. Los modulos de EtherHiding y Contagious
 * Interview implementaran aqui el analisis de AST de JavaScript/npm; el MVP
 * de Proyecto-Pegazus solo cubre deteccion de malware generico desde el
 * backend Python y todavia no invoca este servicio.
 */
export async function analyzePlaceholder(filePath: string): Promise<JsFinding[]> {
  void filePath;
  return [];
}
