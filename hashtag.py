#/usr/bin/python
format_ = format

import csv
import sys
import argparse
import re
import random
import copy;

from pprint import pprint as pp



################################################################################
# Using a database of paths and tags formatted like so:
#
#  path;tag1;tag2;field1=value1;field2=value2;tag3
#
# the hashtag library allows searches on tags and fields using a Boolean search 
# language.  This allows for fluid organization of photos, music, videos, and
# documents.
################################################################################



class HashTagger():

    db = None;

    def __init__(self, filename="database.tag"):
        self.parsedb(filename);


    ################################################################################
    # Detect if string is comment
    ################################################################################
    def iscomment(self, s):
        s = s.strip();
        if not s: return False;
        if s[0] == '#': return True;
        else:           return False;


    ################################################################################
    # Find index where path is
    ################################################################################
    def pathindex(self, path):
        for index in range(len(self.db)):
            if self.db[index]["id"] == path:
               return index;
        return -1;


    ################################################################################
    # Take a row as a string, and return a data structure
    # giving its path and tags
    ################################################################################
    def parserow(self, row):
        if self.iscomment("".join(row)):
           return None;
        ref = {};
        if len(row)>0:
           ref["id"] = row[0];
           ref["tags"] = [];
        else: return None;
        i = 0;
        for el in row[1:]:
            eq = el.split("=");
            if len(eq) > 1:
               if ',' in eq[1]:
                  ref[eq[0]] = eq[1].split(",");
               else: ref[eq[0]] = eq[1];
            else: ref["tags"].append(eq[0]);
        return ref;


    ################################################################################
    # Make file into normal rows
    ################################################################################
    def file2rows(self, filename):
        try:
            self.dbfile = open(filename);
            rows = csv.reader(self.dbfile, delimiter=';', quotechar='"')
        except Exception as e:
            #print(e);
            #sys.exit(1);
            return [];
        rowlist = [r for r in rows];
        self.dbfile.close();
        return rowlist;



    ################################################################################
    # Put rows back into database file
    ################################################################################
    def writeout(self, rows=None, filename="database.tag"):
        try:
          self.dbfile = open(filename, "w+");
        except Exception as e:
          print(e);
          sys.exit(1);
        if not rows: rows = self.db;
        rows = sorted(rows, key = lambda x: x['id']);
        if len(rows)>1:
            for i in range(len(rows)):
                j = (i + 1) % len(rows);
                if rows[i]['id'] == rows[j]['id']: 
                   self.mergerows(rows[j], rows[i]);
                if 'tags' in rows[i]:
                   ts  = rows[i]['tags'];
                   nts = []
                   [nts.append(x) for x in ts if x not in nts]
                   rows[i]['tags'] = sorted(nts);
            for i in range(len(rows)):
                j = (i + 1) % len(rows);
                if rows[i]['id'] == rows[j]['id']: 
                   pass;
                else: self.dbfile.write(self.row2str(rows[i])+"\n");
        self.dbfile.close();



    ################################################################################
    # Convert row back to string
    ################################################################################
    def row2str(self, row):
        if "id" in row: 
              res = str(row["id"])
        else: res = "?"
        if "tags" in row: 
           res = res + ";" + ";".join(row["tags"]);
        for key in row.keys():
            if key=="id" or key=="tags":
               pass
            else:
               dat = row[key];
               if isinstance(row[key], list): dat = ",".join(row[key]);
               res = res + ";" + key + "=" + str(dat);
        return res;
               

    ################################################################################
    # Convert rows in list format to list of data structures
    ################################################################################
    def parserows(self, rows):
        reflist = [];
        for row in rows:
            ref = self.parserow(row);
            if ref: reflist.append(ref);
        return reflist;



    ################################################################################
    # Combine tags from Row A and Row B, with B overwriting A where necessary
    ################################################################################
    def mergerows(self, rowa, rowb):
        rowc = copy.copy(rowa);
        for key in rowb.keys():
            if key == "id":
               pass;
            elif key == "tags":
               for tag in rowb["tags"]:
                   if len(tag)>0 and tag[0] == '-':
                         tag = tag[1:];
                         if tag in rowc["tags"]:
                            rowc["tags"].remove(tag);
                   elif tag not in rowc["tags"]:
                      rowc["tags"].append(tag);
            else:
               rowc[key] = rowb[key];
        return rowc;



    ################################################################################
    # Open a database file, convert rows to data structure, return list of these
    ################################################################################
    def parsedb(self, filename):
        self.db = self.parserows(self.file2rows(filename));
        return self.db;
     


    ################################################################################
    # List unique tags
    ################################################################################
    def tagslist(self, db=None):
        if not db: db = self.db;
        tags = [];
        for d in db:
            if "tags" in d:
               tags = tags + d["tags"]
        return sorted(self.unique(tags));



    ################################################################################
    # List count of tags
    ################################################################################
    def tagscount(self, db=None):
        if not db: db = self.db;
        tags = [];
        for d in db:
            if "tags" in d:
               tags = tags + d["tags"]
        utags = sorted(self.unique(tags));
        tagcs = []; 
        for t in utags:
            tagcs.append(
              [t, tags.count(t)],
            );
        return sorted(tagcs, key=lambda d: d[1], reverse=True);



    ################################################################################
    # Split a query string into tokens
    ################################################################################
    def tokenize(self, s):
        i = 0;
        j = 0;
        tokens = [];
        while i < len(s):
              if (s[i] == '(' or 
                  s[i] == ')' or 
                  s[i] == ',' or 
                  s[i] == '=' or 
                  s[i] == '<' or 
                  s[i] == '/' or 
                  s[i] == '>'):
                 tokens.append(s[i]);
                 j = i;
              elif s[i] != " ":
                 j = i;
                 while i<len(s) and (s[i] != " " and s[i] != ")" and s[i] != ',' and s[i] != '=' and s[i] != '>' and s[i] != '<'):
                       i = i + 1;
                 tokens.append(s[j:i])
                 i = i - 1;
                 j = i;
              i = i + 1;
        return tokens;



    ################################################################################
    # Parse tree node has recursive structure: [left, middle, right]
    # TODO: handle more tokens
    #       comma (','):       denotes sequence, similar to 'or'
    #       shuffler ('shuf'): denotes internal shuffle
    #       numbers (e.g. 3x): denotes number of random entries
    ################################################################################
    def parsetree(self, tokens):

        #print(tokens);

        if   len(tokens) == 1: return tokens[0];
        elif len(tokens) == 0: return tokens;

        i = 0;
        j = 0;
        k = len(tokens)-1; 

        l = [];

        while j < len(tokens):

              # Parentheses: extract expr
              if tokens[j] == '(':
                 if tokens[k] == ')' and '(' not in tokens[j+1:k]:
                    return self.parsetree(tokens[j+1:k]);
                 m = 1;
                 #i = j;
                 while j<k+1:
                       j += 1;
                       if tokens[j] == '(': m += 1;
                       if tokens[j] == ')': m -= 1;
                       if m==0: break;

              elif tokens[j] == "or":
                 if j>i:
                     return [
                       self.parsetree(tokens[i:j]),
                       "or",
                       self.parsetree(tokens[j+1:k+1])
                     ];

              elif tokens[j] == "and":
                 if j>i:
                     return [
                       self.parsetree(tokens[i:j]),
                       "and",
                       self.parsetree(tokens[j+1:k+1])
                     ];


              elif tokens[j] == "not":
                 if j+1==k or (tokens[j+1]=="(" and tokens[k]==")" and "(" not in tokens[j+2:k]):
                     return [
                       None,
                       "not",
                       self.parsetree(tokens[j+1:k+1])
                     ];

              elif tokens[j] == "shuf":
                 if j+1==k or (tokens[j+1]=="(" and tokens[k]==")" and "(" not in tokens[j+2:k]):
                   return [ 
                     None,
                     "shuf",
                     self.parsetree(tokens[j+1:k+1])
                   ];

              elif tokens[j].endswith("x") and tokens[j][:-1].isdigit():
                       if j+1==k or (tokens[j+1]=="(" and tokens[k]==")" and "(" not in tokens[j+2:k]):
                           return [
                                  tokens[j][:-1],
                                  "x",
                                  self.parsetree(tokens[j+1:k+1])
                           ];

              elif tokens[j] == ",":
                   return [
                     self.parsetree(tokens[i:j]),
                     ",",
                     self.parsetree(tokens[j+1:k+1])
                   ];

              j = j + 1;

        return tokens;         


    ################################################################################
    # Helper functions used to integrate results set
    ################################################################################
    def unique(self, a):
        return list(set(a))

    def intersect(self, a, b):
        return list(set(a) & set(b))

    def union(self, a, b):
        return list(set(a) | set(b))

    def concat(self, a, b):
        return a + b;

    def difference(self, a, b):
        return list(set(a) - set(b))


    def subdict(self, d):
        dkeys = list(d.keys());
        newd = {};
        for dk in dkeys:
            if self.f.search(dk):
               newd[dk] = d[dk];
        if len(newd)==1 and 'id' in newd:
           return newd['id'];
        return newd;


    ################################################################################
    # Searches for individual tag values
    ################################################################################
    def searchtag(self, db, query):

        res = [];

        relop = "x"
        if isinstance(query, str):
           field = "tags";
           value = query;
        else: 
           field = query[0];
           relop = query[1];
           value = query[2];

        f = re.compile(field);
        v = re.compile(value);

        if field == "ntags":
            ntags = 0;
            for i in range(len(self.db)):
                d = self.db[i];
                dkeys = d.keys();
                if "tags" in dkeys:
                   ntags = len(d["tags"]);
                if relop == "=":
                   if int(value) == ntags:
                      if i not in res: res.append(i);
                if relop == ">":
                   if ntags > int(value):
                      if i not in res: res.append(i);
                if relop == "<":
                   if ntags < int(value):
                      if i not in res: res.append(i);


        elif relop=="=" or relop == "x":
            for i in range(len(self.db)):
                d = self.db[i];
                dkeys = list(d.keys());
                for dk in dkeys:
                    if f.search(dk):
                       if '#' in str(value):  
                         if dk!="tags": continue;
                       if v.search(str(d[dk])): 
                          if i not in res: res.append(i);
                       elif '!' in str(value):  
                          if i not in res: res.append(i);


        elif relop==">" or relop=="<":
            for i in range(len(self.db)):
                d = self.db[i];
                dkeys = d.keys();
                for dk in dkeys:
                     if f.search(dk):
                        for el in d[field]:
                            if relop == '>' and int(el) > int(value):
                               if i not in res: res.append(i);
                            if relop == '<' and int(el) < int(value):
                               if i not in res: res.append(i);

        return res;



    ################################################################################
    # Searches for results per-node and combines them
    ################################################################################
    def searchtree(self, db=None, tree=None):

        if not tree: tree = self.tree;
        if not db:   db   = self.db;

        if type(tree) is list:

           if len(tree)>2:

               if tree[1] == "and":
                  return self.intersect( 
                    self.searchtree(db, tree[0]),
                    self.searchtree(db, tree[2])
                  )

               elif tree[1] == "or":
                  return self.union( 
                    self.searchtree(db, tree[0]),
                    self.searchtree(db, tree[2])
                  )

               elif tree[1] == "not":
                  paths = [d['id'] for d in db]
                  return self.difference(
                    paths,
                    self.searchtree(db, tree[2])
                  )
               
               elif tree[1] == "shuf":
                  t = self.searchtree(db, tree[2]);
                  random.shuffle(t);
                  return t;


               elif tree[1] == "x":
                  n = int(tree[0]);
                  t = self.searchtree(db, tree[2]);
                  random.shuffle(t);
                  return t[0:n]


               elif tree[1] == ",":
                  return self.concat( 
                    self.searchtree(db, tree[0]),
                    self.searchtree(db, tree[2])
                  )

               elif tree[1] == "=" or tree[1] == ">" or tree[1] == "<":
                  return self.searchtag(db, tree);
               else:
                  return self.searchtag(db, tree);
           else:
               return self.searchtag(db, tree[0]);
        else: 
           return self.searchtag(db, tree);



    def setsorter(self, tokens, i):
        n = len(tokens);
        self.sd = tokens[i];
        i = i+1 if i+1<n else i;
        self.s = re.compile(tokens[i]);
        i = i+1 if i+1<n else i;
        return i;
        


    def setfields(self, tokens):
        i = 0;
        n = len(tokens);
        if '/' not in tokens:
           self.sel = False;
           self.f = re.compile('^id$');
        else: 
           self.sel = True;
           i = tokens.index('/');
           i = i+1 if i+1<n else i;
        if tokens[i] in "><":
           i = self.setsorter(tokens, i);
           if '/' in tokens:
              self.f = re.compile(tokens[i-1]);
           if i+1>=n: return ['.'];
        elif '/' in tokens:
           self.f = re.compile(tokens[i]);
           i = i+1 if i+1<n else i;
           if i+1>=n: return ['.'];
           if tokens[i] in "><":
              i = self.setsorter(tokens, i);
        if len(tokens[i:])==0:
           return ['.'];
        return tokens[i:];



    def sort(self, res):
        if not hasattr(self, 's') or not self.s:
           self.s  = re.compile('^id$');
           self.sd = '>';
        if self.sd == ">": asc = False;
        else:              asc = True;
        import pandas;
        df = pandas.DataFrame(res);
        cs = [];
        for c in list(df.columns):
            if self.s.search(c):
               cs += [c];
        df = df.fillna('');
        df = df.sort_values(by=cs, ascending=asc);
        return df;


    def construct(self, res):
        subset = [];
        #res = self.unique(res);
        for i in res:
            if self.db[i] not in subset:
               subset.append(self.db[i]);
        return subset;


    def deconstruct(self, df):
        cs = [];
        for c in list(df.columns):
            if not self.f.search(c):
               cs += [c];
        df = df.drop(columns=cs);
        cs = list(df.columns)
        if len(cs) == 1 and 'id' in cs:
           return df['id'].to_list();
        self.s = None;
        self.sd = None;
        self.f = None;
        return df.to_dict('records');


    def search(self, query):
        tokens    = self.tokenize(query);
        tokens    = self.setfields(tokens);
        self.tree = self.parsetree(tokens);
        res       = self.searchtree();
        res       = self.construct(res);
        res       = self.sort(res);
        res       = self.deconstruct(res);
        return res;


    ################################################################################
    # Delete rows by path
    ################################################################################
    def delete_entries(self, paths, filename="database.tag"):
        rows = self.file2rows(filename);
        newrows = [];
        for row in rows:
            rowpath = row[0];
            if rowpath not in paths:
               newrows.append(row);
            else: print(row);
        self.rows2file(newrows, filename);



    ################################################################################
    # Delete rows by path
    ################################################################################
    def append_entries(self, rows, filename="database.tag"):
        self.dbfile = open(filename, "a+");
        writer = csv.writer(
          self.dbfile, 
          delimiter=';', 
          quotechar='"', 
          lineterminator='\n'
        )
        for row in rows:
            writer.writerow(row);
        self.dbfile.close();


    ################################################################################
    # Using a tag string and path, append or merge tags into this database
    ################################################################################
    def tagwith(self, path, tags):
        row   = path + ";" + tags;
        ref   = self.parserow(row.split(";"));
        index = self.pathindex(path);
        if index > 0:
              dbref  = self.db[index];
              newref = self.mergerows(dbref, ref); 
              self.db[index] = newref;
        else: self.db.append(ref);


    def squid2ht(self, squid, tags=[], exclude=[], pk="id"):
        squid.query("select * from %s" % (squid.table));
        self.sqldata2ht(squid.data, tags, exclude, pk);


    def sqldata2ht(self, data, tags=[], exclude=[], pk="id"):
        string = "";
        strrows = [];
        for row in data:
            string  += self.sqldict2str(row, tags, exclude, pk);
            strrows += string;
            string  += "\n";
        self.db = parserows(strrows);
        return string;


    def sqldict2str(self, row, tags=[], exclude=[], pk="id"):
        p1 = "";
        p2 = "";
        if pk in row: 
           p1 += row[pk];
        if "tags" in row: 
           p1 = p1 + ";" + ";".join(row["tags"]);
        for key in row.keys():
            if key==pk or key=="tags" or key in exclude:
               pass
            elif key in tags:
               p1 = p1 + ";" + row[key];
            else:
               p2 = p2 + ";" + key + "=" + ",".join(row[key]);
        return res;
