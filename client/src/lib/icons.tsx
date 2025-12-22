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
  MoreHorizontal,
  Package,
  Calendar,
  FileText as FileText2,
  CheckCircle,
  ClipboardList,
  Bell,
  HelpCircle
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
  more: MoreHorizontal,
  package: Package,
  calendar: Calendar
}

// Export individual icons for direct use
export const SearchIcon = Search;
export const DownloadIcon = Download;
export const FileTextIcon = FileText;
export const FolderIcon = Folder;
export const PackageIcon = Package;
export const CalendarIcon = Calendar;
export const AlertIcon = AlertCircle;
export const FilterIcon = Filter;
export const XIcon = X;
export const FileText2Icon = FileText2;
export const CheckCircleIcon = CheckCircle;
export const ClipboardIcon = ClipboardList;
export const BellIcon = Bell;
export const HelpCircleIcon = HelpCircle;

// Configuración global de estilo para iconos
// Stroke width: 1.5px para estilo "lineal fino"
// Size: default 16px o 20px
export const iconStyle = {
  strokeWidth: 1.5,
  className: "shrink-0"
}
