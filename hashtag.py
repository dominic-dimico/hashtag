#/usr/bin/python

import csv
import sys
import argparse
import re

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




################################################################################
# Detect if string is comment
################################################################################
def iscomment(s):
    s = s.strip();
    if not s: return False;
    if s[0] == '#': return True;
    else:           return False;



################################################################################
# Take a row as a string, and return a data structure
# giving its path and tags
################################################################################
def parserow(row):
    if iscomment("".join(row)):
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
def file2rows(filename):
    dbfile = open(filename);
    rows = csv.reader(dbfile, delimiter=';', quotechar='"')
    return [r for r in rows];
    dbfile.close();



################################################################################
# Put rows back into database file
################################################################################
def rows2file(rows, filename="database.tag"):
    dbfile = open(filename, "w+");
    rows = sorted(rows, key = lambda x: x['path']);
    for i in range(len(rows)):
        ts  = rows[i]['tags'];
        nts = []
        [nts.append(x) for x in ts if x not in nts]
        rows[i]['tags'] = sorted(nts);
    for row in rows:
        dbfile.write(row2str(row)+"\n");
    dbfile.close();



################################################################################
# Convert row back to string
################################################################################
def row2str(row):
    if "path" in row: 
       res = row["path"]
    if "tags" in row: 
       res = res + ";" + ";".join(row["tags"]);
    for key in row.keys():
        if key=="path" or key=="tags":
           pass
        else:
           res = res + ";" + key + "=" + row[key];
    return res;
           

################################################################################
# Convert rows in list form to list of data structures
################################################################################
def parserows(rows):
    reflist = [];
    for row in rows:
        ref = parserow(row);
        if ref: reflist.append(ref);
    return reflist;



################################################################################
# Combine tags from Row A and Row B, with B overwriting A where necessary
################################################################################
def mergerows(rowa, rowb):
    rowc = dict(rowa);
    for key in rowb.keys():
        if key == "path":
           pass;
        elif key == "tags":
           for tag in rowb["tags"]:
               if tag not in rowc["tags"]:
                  rowc["tags"].append(tag);
        else:
           rowc[key] = rowb[key];
    return rowc;



################################################################################
# Open a database file, convert rows to data structure, return list of these
################################################################################
def parsedb(filename):
    return parserows(file2rows(filename));
 


################################################################################
# List unique tags
################################################################################
def tagslist(database):
    tags = [];
    for d in database:
        if "tags" in d:
           tags = tags + d["tags"]
    return sorted(unique(tags));



################################################################################
# Split a query string into tokens
################################################################################
def tokenize(s):
    i = 0;
    j = 0;
    tokens = [];
    while i < len(s):
          if s[i] == '(' or s[i] == ')':
             tokens.append(s[i]);
             j = i;
          elif s[i] != " ":
             j = i;
             while i<len(s) and (s[i] != " " and s[i] != ")"):
                   i = i + 1;
             tokens.append(s[j:i])
             i = i - 1;
             j = i;
          i = i + 1;
    return tokens;



################################################################################
# Parse tree node has recursive structure: [left, middle, right]
################################################################################
def parsetree(tokens):

    if   len(tokens) == 1: return tokens[0];
    elif len(tokens) == 0: return None;

    i = 0;
    j = 0;
    k = len(tokens)-1; 

    while j < len(tokens):

          # Parentheses: extract expr
          if tokens[j] == '(':
             while k > 0:
                   if tokens[k] == ')':
                      expr = tokens[j+1:k];
                      return parsetree(expr);
                   k = k - 1

          elif tokens[j] == "or":
             return [
               parsetree(tokens[i:j]),
               "or",
               parsetree(tokens[j+1:k+1])
             ];

          elif tokens[j] == "and":
             return [
               parsetree(tokens[i:j]),
               "and",
               parsetree(tokens[j+1:k+1])
             ];

          elif tokens[j] == "not":
             return [
               None,
               "not",
               parsetree(tokens[j+1:k+1])
             ];

          j = j + 1;
             


################################################################################
# Helper functions used to integrate results set
################################################################################
def unique(a):
    return list(set(a))

def intersect(a, b):
    return list(set(a) & set(b))

def union(a, b):
    return list(set(a) | set(b))

def difference(a, b):
    return list(set(a) - set(b))



################################################################################
# Searches for individual tag values
################################################################################
def searchtag(db, query):

    res = [];
    eq = query.split("=");

    if len(eq) > 1:
       field = eq[0];
       value = eq[1];
    else: 
       field = "tags";
       value = eq[0];

    for d in db:
        dkeys = d.keys();
        if field in dkeys:
           if value in d[field]:
              res.append(d["path"]);

    return res;



################################################################################
# Searches for results per-node and combines them
################################################################################
def searchtree(db, tree):

    if type(tree) is list:

       if tree[1] == "and":
          return intersect( 
            searchtree(db, tree[0]),
            searchtree(db, tree[2])
          )

       elif tree[1] == "or":
          return union( 
            searchtree(db, tree[0]),
            searchtree(db, tree[2])
          )

       elif tree[1] == "not":
          paths = [d['path'] for d in db]
          return difference(
            paths,
            searchtree(db, tree[2])
          )

    else: 
       return searchtag(db, tree);



################################################################################
# Delete rows by path
################################################################################
def delete_entries(paths, filename="database.tag"):
    rows = file2rows(filename);
    newrows = [];
    for row in rows:
        rowpath = row[0];
        if rowpath not in paths:
           newrows.append(row);
        else: print row;
    rows2file(newrows, filename);



################################################################################
# Delete rows by path
################################################################################
def append_entries(rows, filename="database.tag"):
    dbfile = open(filename, "a+");
    writer = csv.writer(
      dbfile, 
      delimiter=';', 
      quotechar='"', 
      lineterminator='\n'
    )
    for row in rows:
        writer.writerow(row);
    dbfile.close();


