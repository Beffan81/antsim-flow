import { useState, useEffect, useCallback } from 'react';

export function usePersistedState<T>(
  key: string,
  defaultValue: T,
  validator?: (value: any) => value is T
): [T, (value: T | ((prev: T) => T)) => void, { reset: () => void; isLoaded: boolean }] {
  const [isLoaded, setIsLoaded] = useState(false);
  const [state, setState] = useState<T>(defaultValue);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(key);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (!validator || validator(parsed)) {
          setState(parsed);
        } else {
          console.warn(`Invalid persisted data for key "${key}", using default`);
        }
      }
    } catch (error) {
      console.error(`Error loading persisted state for key "${key}":`, error);
    } finally {
      setIsLoaded(true);
    }
  }, [key, validator]);

  // Save to localStorage whenever state changes
  const setPersistedState = useCallback((value: T | ((prev: T) => T)) => {
    setState(prevState => {
      const newState = typeof value === 'function' ? (value as (prev: T) => T)(prevState) : value;
      
      try {
        localStorage.setItem(key, JSON.stringify(newState));
      } catch (error) {
        console.error(`Error saving persisted state for key "${key}":`, error);
      }
      
      return newState;
    });
  }, [key]);

  const reset = useCallback(() => {
    setState(defaultValue);
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error(`Error removing persisted state for key "${key}":`, error);
    }
  }, [key, defaultValue]);

  return [state, setPersistedState, { reset, isLoaded }];
}