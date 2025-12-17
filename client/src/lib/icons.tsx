import { 
  Loader2, 
  Search, 
  Download, 
  FileText, 
  Folder, 
  ChevronRight, 
  Check, 
  X, 
  AlertCircle,
  Filter,
  Grid,
  List,
  MoreHorizontal
} from "lucide-react"

export const Icons = {
  spinner: Loader2,
  search: Search,
  download: Download,
  file: FileText,
  folder: Folder,
  chevronRight: ChevronRight,
  check: Check,
  close: X,
  alert: AlertCircle,
  filter: Filter,
  grid: Grid,
  list: List,
  more: MoreHorizontal
}

// Configuración global de estilo para iconos
// Stroke width: 1.5px para estilo "lineal fino"
// Size: default 16px o 20px
export const iconStyle = {
  strokeWidth: 1.5,
  className: "shrink-0"
}
