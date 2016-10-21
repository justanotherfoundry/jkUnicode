#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division
import os, weakref
from jkUnicode.tools.jsonhelpers import json_path, json_to_file, dict_from_file


class Orthography(object):
	
	def __init__(self, info_obj, code, script, territory, info_dict):
		self._info = weakref.ref(info_obj)
		self.code = code
		self.script = script
		self.territory = territory
		self.from_dict(info_dict)
	
	
	def from_dict(self, info_dict):
		self.name = info_dict.get("name", None)
		uni_info = info_dict.get("unicodes", {})
		self.unicodes_base        = set(uni_info.get("base", []))
		self.unicodes_optional    = set(uni_info.get("optional", [])) - self.unicodes_base
		self.unicodes_punctuation = set(uni_info.get("punctuation", []))
		self.scan_ok = False
	
	
	def fill_from_default_orthography(self):
		# Sometimes the base unicodes are empty for a variant.
		# Try to fill them in from the default variant.
		# Call this only after the whole list of orthographies is present, or it will fail.
		if self.territory != "dflt":
			#print self.code, self.script, self.territory
			parent = self._info().orthography(self.code, self.script)
			if parent is None:
				print "WARNING: No parent orthography found for %s/%s/%s" % (self.code, self.script, self.territory)
			else:
				#print "    Parent:", parent.code, parent.script, parent.territory
				# Set attributes from parent (there may be empty attributes remaining ...?)
				for attr in ["unicodes_base", "unicodes_optional", "unicodes_punctuation"]:
					if getattr(self, attr) == set():
						parent_set = getattr(parent, attr)
						if parent_set:
							#print "    Filled from parent:", attr
							setattr(self, attr, parent_set)
	
	
	def support_full(self, cmap):
		if not self.scan_ok:
			self.scan_cmap(cmap)
		if self.num_missing_base == 0 and self.num_missing_optional == 0 and self.num_missing_punctuation == 0:
			return True
		return False
	
	
	def support_basic(self, cmap):
		if not self.scan_ok:
			self.scan_cmap(cmap)
		if self.num_missing_base == 0 and self.num_missing_optional != 0 and self.num_missing_punctuation == 0:
			return True
		return False
	
	
	def support_minimal(self, cmap):
		if not self.scan_ok:
			self.scan_cmap(cmap)
		if self.num_missing_base == 0 and self.num_missing_optional != 0 and self.num_missing_punctuation != 0:
			return True
		return False
	
	
	def scan_cmap(self, cmap):
		cmap_set = set(cmap)
		# Check for missing chars
		self.missing_base        = self.unicodes_base        - cmap_set
		self.missing_optional    = self.unicodes_optional    - cmap_set
		self.missing_punctuation = self.unicodes_punctuation - cmap_set
		
		self.num_missing_base        = len(self.missing_base)
		self.num_missing_optional    = len(self.missing_optional)
		self.num_missing_punctuation = len(self.missing_punctuation)
		
		# Calculate percentage
		self.base_pc        = 1 - self.num_missing_base / len(self.unicodes_base) if self.unicodes_base else 0
		self.optional_pc    = 1 - self.num_missing_optional / len(self.unicodes_optional) if self.unicodes_optional else 0
		self.punctuation_pc = 1 - self.num_missing_punctuation / len(self.unicodes_punctuation) if self.unicodes_punctuation else 0
		
		self.scan_ok = True
	
	
	def forget_cmap(self):
		self.scan_ok = False
	
	def __repr__(self):
		return u'<Orthography "%s">' % self.name

class OrthographyInfo(object):
	def __init__(self):
		data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "json")
		master = dict_from_file(data_path, "language_characters")
		
		self.orthographies = []
		self._index = {}
		i = 0
		for code, script_dict in master.items():
			#print code, script_dict
			for script, territory_dict in script_dict.items():
				#print script, territory_dict
				for territory, info in territory_dict.items():
					#print territory, info
					self.orthographies.append(Orthography(self, code, script, territory, info))
					self._index[(code, script, territory)] = i
					i += 1
		for o in self.orthographies:
			o.fill_from_default_orthography()
	
	def orthography(self, code, script="DFLT", territory="dflt"):
		i = self._index.get((code, script, territory), None)
		if i is None:
			return None
		return self.orthographies[i]
	
	def scan_cmap(self, cmap):
		for o in self.orthographies:
			o.scan_cmap(cmap)
	
	def list_supported_orthographies(self, cmap, full_only=True):
		result = []
		for o in self.orthographies:
			if full_only:
				if o.support_full(cmap):
					result.append(o.name)
			else:
				if o.support_basic(cmap):
					result.append(o.name)
		return sorted(result)
	
	def list_supported_orthographies_minimum(self, cmap):
		result = []
		for o in self.orthographies:
			if o.support_minimal(cmap):
				result.append(o.name)
		return sorted(result)
	
	#def __getitem__(self, key):
	#	return self.orthographies[key]
	
	def __len__(self):
		return len(self.orthographies)
	
	def __repr__(self):
		return u"<OrthographyInfo with %i orthographies>" % len(self)


def test_scan():
	from time import time
	from fontTools.ttLib import TTFont
	from htmlGenerator.fonttools.sfnt import get_cmap
	cmap = get_cmap(TTFont("/Users/jens/Code/HTMLGenerator/Lib/testdata/consola.ttf"))
	start = time()
	o = OrthographyInfo()
	print o
	#for ot in o.orthographies:
	#	print ot.name
	full = o.list_supported_orthographies(cmap, full_only=True)
	base = o.list_supported_orthographies(cmap, full_only=False)
	mini = o.list_supported_orthographies_minimum(cmap)
	stop = time()
	print "\nFull support:", len(full), "orthography" if len(base) == 1 else "orthographies"
	print ", ".join(sorted(full))
	base = [r for r in base if not r in full]
	print "\nBasic support:", len(base), "orthography" if len(base) == 1 else "orthographies"
	print ", ".join(sorted(base))
	mini = [r for r in mini if not r in full]
	print "\nMinimal support (no punctuation):", len(mini), "orthography" if len(mini) == 1 else "orthographies"
	print ", ".join(sorted(mini))
	print stop - start
	
	print o.orthography("en", "DFLT", "ZA").unicodes_base


if __name__ == "__main__":
	#o = OrthographyInfo()
	#print o
	test_scan()