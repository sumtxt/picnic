-- Execute this in your Supabase SQL Editor

-- Create journal_preferences table (references auth.users directly)
CREATE TABLE public.journal_preferences (
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  journal_short TEXT NOT NULL,
  is_hidden BOOLEAN DEFAULT false NOT NULL,
  PRIMARY KEY (user_id, journal_short)
);

-- Enable Row Level Security
ALTER TABLE public.journal_preferences ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for journal_preferences
CREATE POLICY "Users can view own journal preferences" ON public.journal_preferences
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own journal preferences" ON public.journal_preferences
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own journal preferences" ON public.journal_preferences
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own journal preferences" ON public.journal_preferences
  FOR DELETE USING (auth.uid() = user_id);