import { useState, useEffect, useCallback, useRef } from 'react';
import { Check, ChevronsUpDown, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { getProjectOptionsSearch, handleApiError } from '@/lib/api';

interface ProjectComboboxProps {
  value?: string;
  onValueChange: (value: string) => void;
  disabled?: boolean;
}

export function ProjectCombobox({ value, onValueChange, disabled }: ProjectComboboxProps) {
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [options, setOptions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const searchProjects = useCallback(async (query: string) => {
    if (!query || query.length < 1) {
      setOptions([]);
      return;
    }

    setLoading(true);
    try {
      const results = await getProjectOptionsSearch(query, 50);
      setOptions(results);
      if (results.length === 0) {
        toast.error('No se encontraron proyectos con ese código');
      }
    } catch (error) {
      toast.error(handleApiError(error));
      setOptions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(() => {
      searchProjects(searchQuery);
    }, 300);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [searchQuery, searchProjects]);

  const handleSelect = (selectedValue: string) => {
    onValueChange(selectedValue === value ? '' : selectedValue);
    setOpen(false);
  };

  const displayValue = value || 'Escribe para buscar proyecto...';

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className={cn(
            'w-full justify-between font-normal',
            !value && 'text-muted-foreground'
          )}
        >
          <span className="truncate">{displayValue}</span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Escribe código de proyecto..."
            value={searchQuery}
            onValueChange={setSearchQuery}
          />
          <CommandList>
            {loading && (
              <div className="flex items-center justify-center py-6 text-sm text-muted-foreground">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Buscando...
              </div>
            )}
            {!loading && searchQuery && options.length === 0 && (
              <CommandEmpty>No se encontraron proyectos</CommandEmpty>
            )}
            {!loading && !searchQuery && (
              <div className="py-6 text-center text-sm text-muted-foreground">
                Escribe para buscar proyectos
              </div>
            )}
            {!loading && options.length > 0 && (
              <CommandGroup>
                {options.map((option) => (
                  <CommandItem
                    key={option}
                    value={option}
                    onSelect={() => handleSelect(option)}
                  >
                    <Check
                      className={cn(
                        'mr-2 h-4 w-4',
                        value === option ? 'opacity-100' : 'opacity-0'
                      )}
                    />
                    {option}
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
