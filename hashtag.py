#/usr/bin/python

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
            if self.db[index]["path"] == path:
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
           ref["path"] = row[0];
           ref["tags"] = [];
        else: return None;
        i = 0;
        for el in row[1:]:
            eq = el.split("=");
            if len(eq) > 1:
               ref[eq[0]] = eq[1].split(",");
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
            print(e);
            sys.exit(1);
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
        rows = sorted(rows, key = lambda x: x['path']);
        if len(rows)>1:
            for i in range(len(rows)):
                j = (i + 1) % len(rows);
                if rows[i]['path'] == rows[j]['path']: 
                   self.mergerows(rows[j], rows[i]);
                ts  = rows[i]['tags'];
                nts = []
                [nts.append(x) for x in ts if x not in nts]
                rows[i]['tags'] = sorted(nts);
            for i in range(len(rows)):
                j = (i + 1) % len(rows);
                if rows[i]['path'] == rows[j]['path']: 
                   pass;
                else: self.dbfile.write(self.row2str(rows[i])+"\n");
        self.dbfile.close();



    ################################################################################
    # Convert row back to string
    ################################################################################
    def row2str(self, row):
        if "path" in row: 
           res = row["path"]
        if "tags" in row: 
           res = res + ";" + ";".join(row["tags"]);
        for key in row.keys():
            if key=="path" or key=="tags":
               pass
            else:
               #print(key, row[key]);
               res = res + ";" + key + "=" + ",".join(row[key]);
        return res;
               

    ################################################################################
    # Convert rows in list form to list of data structures
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
            if key == "path":
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
              if s[i] == '(' or s[i] == ')' or s[i] == ',' or s[i] == '=' or s[i] == '<' or s[i] == '>':
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


        if field == "ntags":
            ntags = 0;
            for d in self.db:
                dkeys = d.keys();
                if "tags" in dkeys:
                   ntags = len(d["tags"]);
                if relop == "=":
                   if int(value) == ntags:
                      res.append(d["path"]);
                if relop == ">":
                   if ntags > int(value):
                      res.append(d["path"]);
                if relop == "<":
                   if ntags < int(value):
                      res.append(d["path"]);


        elif relop=="x":
            for d in self.db:
                dkeys = d.keys();
                if field in dkeys:
                   if value in d[field]:
                      res.append(d["path"]);

        elif relop=="=":
            for d in self.db:
                dkeys = d.keys();
                if value == '?':
                  if field not in dkeys:
                     res.append(d["path"]);
                elif field in dkeys:
                  if value in d[field]:
                     res.append(d["path"]);


        elif relop==">":
             for d in self.db:
                 dkeys = d.keys();
                 if field in dkeys:
                    for el in d[field]:
                        if int(el) > int(value):
                           res.append(d["path"]);

        elif relop=="<":
             for d in self.db:
                 dkeys = d.keys();
                 if field in dkeys:
                    for el in d[field]:
                        if int(el) < int(value):
                           res.append(d["path"]);

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
                  paths = [d['path'] for d in db]
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


    def search(self, query):
        tokens    = self.tokenize(query);
        self.tree = self.parsetree(tokens);
        res       = self.searchtree();
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
