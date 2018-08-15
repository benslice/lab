#!/usr/bin/env python3
doc = """

lab.
A plain-text electronic lab notebook.

Usage:
   lab [options] open <filename> 
   lab [options] new 
   lab [options] last
   lab [options] list [projects | keywords]
   lab [options] search <search_string>
   lab [options] todo
   lab [options] validate
   lab [options] replace <string1> <string2>
   lab shots

Options:
  -h --help             Show this help
  -p --project=<proj>   project selector            (new, last, list, search)
  -k --keywords=kwds    keyword selectors           (new, last, list, search)
  -d --date=<datestr>   Date specifier YYMMDD                     (new, list)
  -l --long             Long                                   (list, search)
  -a --attachments      Attachments                        (last, list, open)
  -n --number=<int>     Number    [default: 15]                        (list)


Notes:
   `search` is implemented with fgrep, and does not support regex
   Print a ToDo list with (e.g.)
       lab search '[ ]' -l | enscript -r -2
   "lab todo" is now an alias for "lab search '[ ]'

"""

from docopt import docopt
import subprocess
import os
import sys



## get global options 
# check environment variables first
# fall back to defaults relative to lab executable


exe_dir = os.path.dirname(os.path.realpath(sys.argv[0]))

entry_dir = os.getenv('LAB_ENTRY_DIR', default=exe_dir+'/entries/')
shot_dir = os.getenv('LAB_SHOT_DIR', default=exe_dir+'/shots/')
jekyll_dir = os.getenv('LAB_JEKYLL_DIR', default=exe_dir+'/site/_posts/')

# Everything is currently geared for OSX
# Attachments will be opened in a text editor, or using the open command to lauch the
# right program. Any file with an extention not on these list will be "revealed" in Finder.

# extensions to open in OS default text editor (text-edit)
text_types = os.getenv('LAB_TEXT_EXT', default='m,c,md,txt,tsv,csv')
text_types = text_types.split(',')

# extensions to open with system open() 
open_types = os.getenv('LAB_OPEN_EXT', default='pdf,xls,xlsx,doc,docx,jpg,pptx')
open_types = open_types.split(',')


class entry:
   """
   Holds a single entry
   """
   def __init__(self, args=None, folder=None, filename=None, date=None, location='',
         project='entry', keywords='', previous='', next=''):
      """
      read in entry from a file or create a blank entry
      if filename is passed load it
      passed in values may be overwritten by file contents (e.g. project)
      
      """

      # overwrite some passed in Nones
      if keywords is None:
         keywords = ''

      # store any variables passed in 
      self.folder=folder# default to entry_dir, must exist
      self.filename=filename # short form, must exist
      self.date=date         # short form e.g. 170819 (str) default to today
      self.date_str=None     # long form e.g. September 16, 2017
      self.location=location # optional
      self.project=project   # only one allowed, default to "entry"
      self.keywords=keywords # always a string, csv, spaces optional
      self.previous=previous # full filename, one line/file only
      self.next=next         # full filename, one line/file only

      # also add sections that can't be passed in
      self.goal = ''
      self.log = ''
      self.summary = ''
      self.attachments = ''

      if self.date is None:
         import datetime
         today = datetime.date.today()
         self.date = today.strftime('%y%m%d')

      if self.folder is None:
         self.folder = entry_dir

      if self.filename is None:
         self.filename = self.date + '_' + self.project + '.md'

      if self.project is None:
         self.project = 'entry'

      if os.path.exists(os.path.join(self.folder, self.filename)):
         try:
            contents = self.parse_sections(os.path.join(self.folder , self.filename))
            self.date        = contents['Date']
            self.date_str    = contents['DateStr']
            self.location    = contents['Location']
            self.project     = contents['Project']
            self.keywords    = contents['Keywords']
            self.goal        = contents['Goal']
            self.log         = contents['Log Entry']
            self.summary     = contents['Summary']
            self.attachments = contents['Attachments']
            self.previous    = contents['Previous'] 
            self.next        = contents['Next']
         except KeyError as err:
            sys.exit('error parsing %s section of %s' % (err, self.filename))
         except:
            sys.exit('unknown error parsing %s' % self.filename)

   def has_keywords(self, keywords):
      """ parse keyword strings to sets and check for intersection """
      k_inpt = set([x.strip() for x in keywords.split(',')])
      k_self = set([x.strip() for x in self.keywords.split(',')])
      if len(k_inpt & k_self) > 0:
         return True
      else:
         return False

   def get_date(self):
      """ return (and set) string verion of date """
      if self.date_str is None:
         import datetime
         y = 2000 + int(self.date[0:2])
         m = int(self.date[2:4])
         d = int(self.date[4:])
         today = datetime.date(y, m, d)
         self.date_str = today.strftime('%B %d, %Y')

      return self.date_str


   def get_jekyll_date(self):
      """ return string verion of date in jekyll format """
      import datetime
      y = 2000 + int(self.date[0:2])
      m = int(self.date[2:4])
      d = int(self.date[4:])
      today = datetime.date(y, m, d)
      j_date_str = today.strftime('%Y-%m-%d')

      return j_date_str

   def link_next(self, entry):
      """ overwrite Next section with entry filename """
      self.next = entry.filename

   def link_prev(self, entry):
      """ overwrite Previous section with entry filename """
      self.previous = entry.filename

   def to_file(self, filename=None):
      """
      write entry out to filename 
      assumes full path, or entry_dir
      """
      if filename is None:
         filename = os.path.join(entry_dir, self.filename)

      fid = open(filename, 'w')

      print(self.get_date(), file=fid)
      print('='.rjust(len(self.date_str), '='), file=fid)
      print(self.location, file=fid)
      print('', file=fid)

      titles = ['Project', 'Keywords', 'Goal', 'Log Entry', 
            'Summary', 'Attachments', 'Previous', 'Next']
      sections = [self.project, self.keywords, self.goal, self.log, 
            self.summary, self.attachments, self.previous, self.next]
      for t,s in zip(titles, sections):
         print(t, file=fid)
         print('-'.rjust(len(t), '-'), file=fid)
         print(s, file=fid)
         print('', file=fid)

      fid.close()


   def to_jekyll(self):
      """
      write entry out to a jekyll post
      """
      # jekyll filename yyyy-mm-dd-title-title...md

      # I don't have titles, for now date/category should be enough
      filename = self.get_jekyll_date()
      filename += '-' + self.project + '.md'

      fid = open(os.path.join(jekyll_dir,filename), 'w')


      # yaml front matter
      print('---', file=fid)
      print('layout: post', file=fid)
      print('title: %s' % self.goal, file=fid)
      print('project: %s' % self.project, file=fid)
      print('date: %s' % self.get_jekyll_date(), file=fid)
      print('---', file=fid)


      # then print the rest in markdown as before
      print(self.get_date(), file=fid)
      print('='.rjust(len(self.date_str), '='), file=fid)
      print(self.location, file=fid)
      print('', file=fid)

      titles = ['Project', 'Keywords', 'Goal', 'Log Entry', 
            'Summary', 'Attachments', 'Previous', 'Next']
      sections = [self.project, self.keywords, self.goal, self.log, 
            self.summary, self.attachments, self.previous, self.next]
      for t,s in zip(titles, sections):
         print(t, file=fid)
         print('-'.rjust(len(t), '-'), file=fid)
         print(s, file=fid)
         print('', file=fid)

      fid.close()

   def parse_sections(self, fullpath):
      """ return contents of a file in a dict with section keys """
      result = {}
      fid = open(fullpath)

      # Date is first and different in every file, so parse by hand
      import datetime
      result['DateStr'] = fid.readline().strip()
      line = fid.readline()
      d = datetime.datetime.strptime(result['DateStr'], '%B %d, %Y')
      result['Date'] = d.strftime('%y%m%d')

      sec = ['Project', 'Keywords', 'Goal', 'Log Entry', 'Summary', 'Attachments', 'Previous', 'Next']
      sec.append('never find me')
      sec.reverse()

      this_section = 'Location'
      next_section = sec.pop()
      paragraph = ''

      for line in fid:
         if line.startswith(next_section):
            result[this_section] = paragraph.strip()
            paragraph = ''
            this_section = next_section
            next_section = sec.pop()
         elif line.startswith('----'):
            pass
         else:
            paragraph += line

         # store the results
         result[this_section] = paragraph.strip()

      return result

def command_new(args):
   """create and open a new entry"""

   new_entry = entry(date=args['--date'], 
                     project=args['--project'],
                     keywords=args['--keywords'])

   # get last entry in this project, if exists, and link them
   # only do this if "today," i.e. no --date passed
   if args['--date'] is None:
      old_entries = get_entries(project=args['--project'])
      if len(old_entries) > 0:
         old_entry = old_entries[-1]
         old_entry.link_next(new_entry)
         new_entry.link_prev(old_entry)

         # rewrite old file
         old_entry.to_file()

   new_entry.to_file()

   # lastly, open the file, fudging args
   args['<filename>'] = new_entry.filename
   command_open(args, folder=new_entry.folder)

def command_last(args):
   """open the last entry in the notebook by name (not timestamp) """
   
   entries = get_entries(project=args['--project'],
                              keywords=args['--keywords'])

   entries = [e.filename for e in entries]
   entries.sort()

   if len(entries) < 1:
      sys.exit('no matching entries found')
   else:
      if args['--attachments']:
         for a in entry(filename=entries[-1]).attachments.split('\n'):
            util_open_path(a.strip())

      subprocess.call(['vim', os.path.join(entry_dir, entries[-1])])

def command_open(args, folder=entry_dir):
   """
   open the filename provided
   """
   filename = args['<filename>']
   target = os.path.join(folder, filename)

   if os.path.exists(target):
      if args['--attachments']:
         for a in entry(filename=filename, folder=folder).attachments.split('\n'):
            util_open_path(a.strip())

      subprocess.call(['vim', target])
   else:
      sys.exit('target file does not exist:\n%s' % (target))

def command_list(args):
   """
   list the entries in the entry folder
   -n <Num> list the last n (default 15)
   -a will filter by has attachments
   -l is the long list
   -l -a will additionally list attachments

   -l with "keywords" or "projects" will wrap items in quotes

   """
   # apply global option filters 
   entries = get_entries(project=args['--project'],
                              date=args['--date'],
                              keywords=args['--keywords'])

   # special commands, list projects or keywords
   if args['projects']:

      project_list = [x.project for x in entries]
      project_set = sorted(list(set(project_list)))

      if args['--long']:
         num_entries = [project_list.count(x) for x in project_set]

         # also wrap in quotes
         project_set = ["'"+x+"'" for x in project_set]

         # sort indexes, using the count as the sorting key
         ix = sorted(range(len(project_set)), reverse=True, key=lambda k: num_entries[k])
         num_entries = [num_entries[k] for k in ix]
         project_set = [project_set[k] for k in ix]
         field_width = max([len(x) for x in project_set])+4
         format_string = '{0: <%s} {1: >3d}' % field_width

         for x,y in zip(project_set, num_entries):
            print(format_string.format(x,y))

      else:
         [print(x) for x in project_set]

   elif args['keywords']:
      keyword_list = []
      for e in entries:
         keyword_list.extend([x.strip() for x in e.keywords.split(',')])

      keyword_set = sorted(list(set(keyword_list)))

      if args['--long']:
         num_entries = [keyword_list.count(x) for x in keyword_set]

         keyword_set = ["'"+x+"'" for x in keyword_set]
         ix = sorted(range(len(keyword_set)), reverse=True, key=lambda k: num_entries[k])
         num_entries = [num_entries[k] for k in ix]
         keyword_set = [keyword_set[k] for k in ix]
         field_width = max([len(x) for x in keyword_set])+4
         format_string = '{0: <%s} {1: >3d}' % field_width

         for x,y in zip(keyword_set, num_entries):
            print(format_string.format(x,y))

      else:
         [print(x) for x in keyword_set]

   # default, list entries
   else:

      if args['--attachments']:
         entries = [x for x in entries if len(x.attachments) > 1]

      if args['--number']:
         N = int(args['--number'])
         if len(entries) >= N:
            entries = entries[-N:]

      # long list entries
      if args['--long']:
         for e in entries:
            f = e.filename.split('/')[-1]
            s = e.summary.replace('\n', ' ')
            if len(s) > 70:
               s = s[:70]
            print('\t'.join([f, s]))
            if args['--attachments']:
               # indent and print out filenames, not paths, plus an extra newline
               for a in e.attachments.split('\n'):
                  print('\t' + os.path.basename(a))
               print()


      # short list entries, filename only
      else:
         for e in entries:
            print(e.filename.split('/')[-1])


def command_validate(args):
   """ 
   validation routines:
   Check for missing attachments
   """
   entries = get_entries(project=args['--project'],
                              date=args['--date'],
                              keywords=args['--keywords'])

   # check for missing attachments
   for e in entries:
      if len(e.attachments) > 0:
         for a in e.attachments.split('\n'):
            # remove escape sequences (for files with ' ' in the name)
            a = a.replace('\\', '')
            if not os.path.exists(a.strip()):
               print(e.filename + '\t' + a)


   
def command_replace(args):
   """
   In the selected entries, replace all instances of one string with another.
   This is meant for attachments, but will also be applied to the Log Entry section.
   Files with a change get their names printed.
   """
   entries = get_entries(project=args['--project'],
                              date=args['--date'],
                              keywords=args['--keywords'])

   for e in entries:
      if (args['<string1>'] in e.log) or (args['<string1>'] in e.attachments):
         print(e.filename)
         e.log = e.log.replace(args['<string1>'], args['<string2>'])
         e.attachments = e.attachments.replace(args['<string1>'], args['<string2>'])
         e.to_file()


def util_open_path(path, reveal=False, text=False):
   """ invoke system OPEN or REVEAL IN FINDER on a path or file """
   command = ['open']


   # if not a folder, check the file type
   if not os.path.isdir(path):
      file_ext = path.split('.')[-1].lower()

      # open these with text-edit
      if file_ext in text_types:
         text=True

      # reveal anything not in our list
      elif file_ext not in open_types:
         reveal = True

   if reveal:
      command.append('-R')
   if text:
      command.append('-t')

   command.append(path)
   ret_code = subprocess.call(command)
   if ret_code > 0:
      print('failed: %s' % command)
      print('call to "open" returned: '+str(ret_code), file=sys.stderr)

def util_search_todo(args):
   """ an alias for search '[ ]'"""
   args['<search_string>'] = '[ ]'
   util_search(args)

def util_search(args):
   """ does an fgrep """
   entries = get_entries(project=args['--project'],
                              date=args['--date'],
                              keywords=args['--keywords'])
   # back to filenames to pass to fgrep
   entries = [e.filename for e in entries]
   if len(entries) < 1:
      sys.exit('no matching entries found')
   command = ['fgrep']

   # -l for default context...
   if args['--long']:
      command.append('-C2')

   # add color, and case insensitivity defaults
   command.append('--color=auto')
   command.append('-i')

   command.append(args['<search_string>'])
   command.extend(entries)

   #  print(' '.join(command))
   subprocess.call(command, cwd=entry_dir)

def get_entries(project=None, date=None, keywords=None):
   """ return a filtered list of entry objects """

   files = os.listdir(entry_dir)
   files = [e for e in files if e.endswith('.md')]
   files.sort()
   entries = [entry(filename=f) for f in files]

   if project is not None:
      entries = [e for e in entries if e.project == project]

   if date is not None:
      entries = [e for e in entries if e.date == date]

   if keywords is not None:
      entries = [e for e in entries if e.has_keywords(keywords)]

   return entries

if __name__ == '__main__':
   args = docopt(doc)

   if args['new']:
      command_new(args)
   elif args['last']:
      command_last(args)
   elif args['list']:
      command_list(args)
   elif args['open']:
      command_open(args)
   elif args['validate']:
      command_validate(args)
   elif args['shots']:
      util_open_path(shot_dir)
   elif args['search']:
      util_search(args)
   elif args['todo']:
      util_search_todo(args)
   elif args['replace']:
      command_replace(args)
   else:
      print(doc)

