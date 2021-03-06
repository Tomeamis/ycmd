# Copyright (C) 2011, 2012 Google Inc.
#
# This file is part of ycmd.
#
# ycmd is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ycmd is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ycmd.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

import contextlib
import os

from nose.tools import eq_, ok_
from ycmd.completers.cpp import flags
from mock import patch, MagicMock
from types import ModuleType
from ycmd.tests.test_utils import MacOnly, TemporaryTestDir, WindowsOnly
from ycmd.responses import NoExtraConfDetected
from ycmd.tests.clang import TemporaryClangProject
from ycmd.completers.cpp.flags import _ShouldAllowWinStyleFlags

from hamcrest import ( assert_that,
                       calling,
                       contains,
                       empty,
                       equal_to,
                       has_item,
                       not_,
                       raises )


@contextlib.contextmanager
def MockExtraConfModule( flags_for_file_function ):
  module = MagicMock( spec = ModuleType )
  module.is_global_ycm_extra_conf = False
  module.FlagsForFile = flags_for_file_function
  with patch( 'ycmd.extra_conf_store.ModuleForSourceFile',
              return_value = module ):
    yield


def FlagsForFile_NothingReturned_test():
  flags_object = flags.Flags()

  def FlagsForFile( filename ):
    pass

  with MockExtraConfModule( FlagsForFile ):
    flags_list, filename = flags_object.FlagsForFile( '/foo' )
    assert_that( flags_list, empty() )
    assert_that( filename, equal_to( '/foo' ) )


def FlagsForFile_FlagsNotReady_test():
  flags_object = flags.Flags()

  def FlagsForFile( filename ):
    return {
      'flags': [],
      'flags_ready': False
    }

  with MockExtraConfModule( FlagsForFile ):
    flags_list, filename = flags_object.FlagsForFile( '/foo', False )
    eq_( list( flags_list ), [] )
    eq_( filename, '/foo' )


def FlagsForFile_BadNonUnicodeFlagsAreAlsoRemoved_test( *args ):
  flags_object = flags.Flags()

  def FlagsForFile( filename ):
    return {
      'flags': [ bytes( b'-c' ), '-c', bytes( b'-foo' ), '-bar' ]
    }

  with MockExtraConfModule( FlagsForFile ):
    flags_list, _ = flags_object.FlagsForFile( '/foo', False )
    eq_( list( flags_list ), [ '-foo', '-bar' ] )


def FlagsForFile_FlagsCachedByDefault_test():
  flags_object = flags.Flags()

  def FlagsForFile( filename ):
    return {
      'flags': [ '-x', 'c' ]
    }

  with MockExtraConfModule( FlagsForFile ):
    flags_list, _ = flags_object.FlagsForFile( '/foo', False )
    assert_that( flags_list, contains( '-x', 'c' ) )

  def FlagsForFile( filename ):
    return {
      'flags': [ '-x', 'c++' ]
    }

  with MockExtraConfModule( FlagsForFile ):
    flags_list, _ = flags_object.FlagsForFile( '/foo', False )
    assert_that( flags_list, contains( '-x', 'c' ) )


def FlagsForFile_FlagsNotCachedWhenDoCacheIsFalse_test():
  flags_object = flags.Flags()

  def FlagsForFile( filename ):
    return {
      'flags': [ '-x', 'c' ],
      'do_cache': False
    }

  with MockExtraConfModule( FlagsForFile ):
    flags_list, _ = flags_object.FlagsForFile( '/foo', False )
    assert_that( flags_list, contains( '-x', 'c' ) )

  def FlagsForFile( filename ):
    return {
      'flags': [ '-x', 'c++' ]
    }

  with MockExtraConfModule( FlagsForFile ):
    flags_list, _ = flags_object.FlagsForFile( '/foo', False )
    assert_that( flags_list, contains( '-x', 'c++' ) )


def FlagsForFile_FlagsCachedWhenDoCacheIsTrue_test():
  flags_object = flags.Flags()

  def FlagsForFile( filename ):
    return {
      'flags': [ '-x', 'c' ],
      'do_cache': True
    }

  with MockExtraConfModule( FlagsForFile ):
    flags_list, _ = flags_object.FlagsForFile( '/foo', False )
    assert_that( flags_list, contains( '-x', 'c' ) )

  def FlagsForFile( filename ):
    return {
      'flags': [ '-x', 'c++' ]
    }

  with MockExtraConfModule( FlagsForFile ):
    flags_list, _ = flags_object.FlagsForFile( '/foo', False )
    assert_that( flags_list, contains( '-x', 'c' ) )


def FlagsForFile_DoNotMakeRelativePathsAbsoluteByDefault_test():
  flags_object = flags.Flags()

  def FlagsForFile( filename ):
    return {
      'flags': [ '-x', 'c', '-I', 'header' ]
    }

  with MockExtraConfModule( FlagsForFile ):
    flags_list, _ = flags_object.FlagsForFile( '/foo', False )
    assert_that( flags_list,
                 contains( '-x', 'c',
                           '-I', 'header' ) )


def FlagsForFile_MakeRelativePathsAbsoluteIfOptionSpecified_test():
  flags_object = flags.Flags()

  def FlagsForFile( filename ):
    return {
      'flags': [ '-x', 'c', '-I', 'header' ],
      'include_paths_relative_to_dir': '/working_dir/'
    }

  with MockExtraConfModule( FlagsForFile ):
    flags_list, _ = flags_object.FlagsForFile( '/foo', False )
    assert_that( flags_list,
                 contains( '-x', 'c',
                           '-I', os.path.normpath( '/working_dir/header' ) ) )


@MacOnly
@patch( 'ycmd.completers.cpp.flags.MAC_INCLUDE_PATHS',
        [ 'sentinel_value_for_testing' ] )
def FlagsForFile_AddMacIncludePathsWithoutSysroot_test():
  flags_object = flags.Flags()

  def FlagsForFile( filename ):
    return {
      'flags': [ '-test', '--test1', '--test2=test' ]
    }

  with MockExtraConfModule( FlagsForFile ):
    flags_list, _ = flags_object.FlagsForFile( '/foo' )
    assert_that( flags_list, has_item( 'sentinel_value_for_testing' ) )


@MacOnly
@patch( 'ycmd.completers.cpp.flags.MAC_INCLUDE_PATHS',
        [ 'sentinel_value_for_testing' ] )
def FlagsForFile_DoNotAddMacIncludePathsWithSysroot_test():
  flags_object = flags.Flags()

  def FlagsForFile( filename ):
    return {
      'flags': [ '-isysroot', 'test1', '--test2=test' ]
    }

  with MockExtraConfModule( FlagsForFile ):
    flags_list, _ = flags_object.FlagsForFile( '/foo' )
    assert_that( flags_list, not_( has_item( 'sentinel_value_for_testing' ) ) )

  def FlagsForFile( filename ):
    return {
      'flags': [ '-test', '--sysroot', 'test1' ]
    }

  with MockExtraConfModule( FlagsForFile ):
    flags_list, _ = flags_object.FlagsForFile( '/foo' )
    assert_that( flags_list, not_( has_item( 'sentinel_value_for_testing' ) ) )

  def FlagsForFile( filename ):
    return {
      'flags': [ '-test', 'test1', '--sysroot=test' ]
    }

  with MockExtraConfModule( FlagsForFile ):
    flags_list, _ = flags_object.FlagsForFile( '/foo' )
    assert_that( flags_list, not_( has_item( 'sentinel_value_for_testing' ) ) )


def FlagsForFile_OverrideTranslationUnit_test():
  flags_object = flags.Flags()

  def FlagsForFile( filename ):
    return {
      'flags': [],
      'override_filename': 'changed:' + filename
    }

  with MockExtraConfModule( FlagsForFile ):
    flags_list, filename = flags_object.FlagsForFile( '/foo' )
    assert_that( flags_list, contains() )
    assert_that( filename, equal_to( 'changed:/foo' ) )


  def FlagsForFile( filename ):
    return {
      'flags': [],
      'override_filename': filename
    }

  with MockExtraConfModule( FlagsForFile ):
    flags_list, filename = flags_object.FlagsForFile( '/foo' )
    assert_that( flags_list, contains() )
    assert_that( filename, equal_to( '/foo' ) )


  def FlagsForFile( filename ):
    return {
      'flags': [],
      'override_filename': None
    }

  with MockExtraConfModule( FlagsForFile ):
    flags_list, filename = flags_object.FlagsForFile( '/foo' )
    assert_that( flags_list, contains() )
    assert_that( filename, equal_to( '/foo' ) )


  def FlagsForFile( filename ):
    return {
      'flags': [],
    }

  with MockExtraConfModule( FlagsForFile ):
    flags_list, filename = flags_object.FlagsForFile( '/foo' )
    assert_that( flags_list, contains() )
    assert_that( filename, equal_to( '/foo' ) )


  def FlagsForFile( filename ):
    return {
      'flags': [],
      'override_filename': ''
    }

  with MockExtraConfModule( FlagsForFile ):
    flags_list, filename = flags_object.FlagsForFile( '/foo' )
    assert_that( flags_list, contains() )
    assert_that( filename, equal_to( '/foo' ) )


  def FlagsForFile( filename ):
    return {
      'flags': [],
      'override_filename': '0'
    }

  with MockExtraConfModule( FlagsForFile ):
    flags_list, filename = flags_object.FlagsForFile( '/foo' )
    assert_that( flags_list, contains() )
    assert_that( filename, equal_to( '0' ) )


def RemoveUnusedFlags_Passthrough_test():
  eq_( [ '-foo', '-bar' ],
       flags._RemoveUnusedFlags( [ '-foo', '-bar' ],
                                 'file',
                                 _ShouldAllowWinStyleFlags(
                                   [ '-foo', '-bar' ] ) ) )


def RemoveUnusedFlags_RemoveDashC_test():
  expected = [ '-foo', '-bar' ]
  to_remove = [ '-c' ]
  filename = 'file'

  eq_( expected,
       flags._RemoveUnusedFlags( expected + to_remove,
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   expected + to_remove ) ) )

  eq_( expected,
       flags._RemoveUnusedFlags( to_remove + expected,
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   to_remove + expected ) ) )

  eq_( expected,
       flags._RemoveUnusedFlags(
         expected[ :1 ] + to_remove + expected[ -1: ],
         filename,
         _ShouldAllowWinStyleFlags(
           expected[ :1 ] + to_remove + expected[ -1: ] ) ) )


def RemoveUnusedFlags_RemoveColor_test():
  expected = [ '-foo', '-bar' ]
  to_remove = [ '--fcolor-diagnostics' ]
  filename = 'file'

  eq_( expected,
       flags._RemoveUnusedFlags( expected + to_remove,
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   expected + to_remove ) ) )

  eq_( expected,
       flags._RemoveUnusedFlags( to_remove + expected,
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   to_remove + expected ) ) )

  eq_( expected,
       flags._RemoveUnusedFlags(
         expected[ :1 ] + to_remove + expected[ -1: ],
         filename,
         _ShouldAllowWinStyleFlags(
           expected[ :1 ] + to_remove + expected[ -1: ] ) ) )


def RemoveUnusedFlags_RemoveDashO_test():
  expected = [ '-foo', '-bar' ]
  to_remove = [ '-o', 'output_name' ]
  filename = 'file'

  eq_( expected,
       flags._RemoveUnusedFlags( expected + to_remove,
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   expected + to_remove ) ) )

  eq_( expected,
       flags._RemoveUnusedFlags( to_remove + expected,
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   to_remove + expected ) ) )

  eq_( expected,
       flags._RemoveUnusedFlags(
         expected[ :1 ] + to_remove + expected[ -1: ],
         filename,
         _ShouldAllowWinStyleFlags(
           expected[ :1 ] + to_remove + expected[ -1: ] ) ) )


def RemoveUnusedFlags_RemoveMP_test():
  expected = [ '-foo', '-bar' ]
  to_remove = [ '-MP' ]
  filename = 'file'

  eq_( expected,
       flags._RemoveUnusedFlags( expected + to_remove,
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   expected + to_remove ) ) )

  eq_( expected,
       flags._RemoveUnusedFlags( to_remove + expected,
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   to_remove + expected ) ) )

  eq_( expected,
       flags._RemoveUnusedFlags(
         expected[ :1 ] + to_remove + expected[ -1: ],
         filename,
         _ShouldAllowWinStyleFlags(
           expected[ :1 ] + to_remove + expected[ -1: ] ) ) )


def RemoveUnusedFlags_RemoveFilename_test():
  expected = [ 'foo', '-bar' ]
  to_remove = [ 'file' ]
  filename = 'file'

  eq_( expected,
       flags._RemoveUnusedFlags( expected + to_remove,
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   expected + to_remove ) ) )

  eq_( expected,
       flags._RemoveUnusedFlags( expected[ :1 ] + to_remove + expected[ 1: ],
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   expected[ :1 ] + to_remove + expected[ 1: ]
                                 ) ) )

  eq_( expected,
       flags._RemoveUnusedFlags(
         expected[ :1 ] + to_remove + expected[ -1: ],
         filename,
         _ShouldAllowWinStyleFlags(
           expected[ :1 ] + to_remove + expected[ -1: ] ) ) )


def RemoveUnusedFlags_RemoveFlagWithoutPrecedingDashFlag_test():
  expected = [ 'g++', '-foo', '-x', 'c++', '-bar', 'include_dir' ]
  to_remove = [ 'unrelated_file' ]
  filename = 'file'

  eq_( expected,
       flags._RemoveUnusedFlags( expected + to_remove,
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   expected + to_remove ) ) )

  eq_( expected,
       flags._RemoveUnusedFlags( expected[ :1 ] + to_remove + expected[ 1: ],
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   expected[ :1 ] + to_remove + expected[ 1: ]
                                 ) ) )


@WindowsOnly
def RemoveUnusedFlags_RemoveStrayFilenames_CLDriver_test():
  # Only --driver-mode=cl specified.
  expected = [ 'g++', '-foo', '--driver-mode=cl', '-xc++', '-bar',
               'include_dir', '/I', 'include_dir_other' ]
  to_remove = [ '..' ]
  filename = 'file'

  eq_( expected,
       flags._RemoveUnusedFlags( expected + to_remove,
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   expected + to_remove ) ) )

  eq_( expected,
       flags._RemoveUnusedFlags( expected[ :1 ] + to_remove + expected[ 1: ],
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   expected[ :1 ] + to_remove + expected[ 1: ]
                                 ) ) )

  # clang-cl and --driver-mode=cl
  expected = [ 'clang-cl.exe', '-foo', '--driver-mode=cl', '-xc++', '-bar',
               'include_dir', '/I', 'include_dir_other' ]
  to_remove = [ 'unrelated_file' ]
  filename = 'file'

  eq_( expected,
       flags._RemoveUnusedFlags( expected + to_remove,
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   expected + to_remove
                                 ) ) )

  eq_( expected,
       flags._RemoveUnusedFlags( expected[ :1 ] + to_remove + expected[ 1: ],
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   expected[ :1 ] + to_remove + expected[ 1: ]
                                 ) ) )

  # clang-cl only
  expected = [ 'clang-cl.exe', '-foo', '-xc++', '-bar',
               'include_dir', '/I', 'include_dir_other' ]
  to_remove = [ 'unrelated_file' ]
  filename = 'file'

  eq_( expected,
       flags._RemoveUnusedFlags( expected + to_remove,
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   expected + to_remove ) ) )

  eq_( expected,
      flags._RemoveUnusedFlags( expected[ :1 ] + to_remove + expected[ 1: ],
                                filename,
                                _ShouldAllowWinStyleFlags(
                                  expected[ :1 ] + to_remove + expected[ 1: ]
                                ) ) )

  # clang-cl and --driver-mode=gcc
  expected = [ 'clang-cl', '-foo', '-xc++', '--driver-mode=gcc',
               '-bar', 'include_dir' ]
  to_remove = [ 'unrelated_file', '/I', 'include_dir_other' ]
  filename = 'file'

  eq_( expected,
       flags._RemoveUnusedFlags( expected + to_remove,
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   expected + to_remove ) ) )
  eq_( expected,
       flags._RemoveUnusedFlags( expected[ :1 ] + to_remove + expected[ 1: ],
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   expected[ :1 ] + to_remove + expected[ 1: ]
                                 ) ) )


  # cl only with extension
  expected = [ 'cl.EXE', '-foo', '-xc++', '-bar', 'include_dir' ]
  to_remove = [ '-c', 'path\\to\\unrelated_file' ]
  filename = 'file'

  eq_( expected,
       flags._RemoveUnusedFlags( expected + to_remove,
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   expected + to_remove ) ) )
  eq_( expected,
       flags._RemoveUnusedFlags( expected[ :1 ] + to_remove + expected[ 1: ],
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   expected[ :1 ] + to_remove + expected[ 1: ]
                                 ) ) )

  # cl path with Windows separators
  expected = [ 'path\\to\\cl', '-foo', '-xc++', '/I', 'path\\to\\include\\dir' ]
  to_remove = [ '-c', 'path\\to\\unrelated_file' ]
  filename = 'file'

  eq_( expected,
       flags._RemoveUnusedFlags( expected + to_remove,
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   expected + to_remove ) ) )
  eq_( expected,
       flags._RemoveUnusedFlags( expected[ :1 ] + to_remove + expected[ 1: ],
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   expected[ :1 ] + to_remove + expected[ 1: ]
                                 ) ) )



@WindowsOnly
def RemoveUnusedFlags_MultipleDriverModeFlagsWindows_test():
  expected = [ 'g++',
               '--driver-mode=cl',
               '/Zi',
               '-foo',
               '--driver-mode=gcc',
               '--driver-mode=cl',
               'include_dir' ]
  to_remove = [ 'unrelated_file', '/c' ]
  filename = 'file'

  eq_( expected,
       flags._RemoveUnusedFlags( expected + to_remove,
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   expected + to_remove ) ) )
  eq_( expected,
       flags._RemoveUnusedFlags( expected[ :1 ] + to_remove + expected[ 1: ],
                                 filename,
                                 _ShouldAllowWinStyleFlags(
                                   expected[ :1 ] + to_remove + expected[ 1: ]
                                 ) ) )

  flags_expected = [ '/usr/bin/g++', '--driver-mode=cl', '--driver-mode=gcc' ]
  flags_all = [ '/usr/bin/g++',
                '/Zi',
                '--driver-mode=cl',
                '/foo',
                '--driver-mode=gcc' ]
  filename = 'file'

  eq_( flags_expected, flags._RemoveUnusedFlags( flags_all,
                                                 filename,
                                                 _ShouldAllowWinStyleFlags(
                                                   flags_all ) ) )


def RemoveUnusedFlags_Depfiles_test():
  full_flags = [
    '/bin/clang',
    '-x', 'objective-c',
    '-arch', 'armv7',
    '-MMD',
    '-MT', 'dependencies',
    '-MF', 'file',
    '--serialize-diagnostics', 'diagnostics'
  ]

  expected = [
    '/bin/clang',
    '-x', 'objective-c',
    '-arch', 'armv7',
  ]

  assert_that( flags._RemoveUnusedFlags( full_flags,
                                         'test.m',
                                         _ShouldAllowWinStyleFlags(
                                           full_flags ) ),
               contains( *expected ) )


def EnableTypoCorrection_Empty_test():
  eq_( flags._EnableTypoCorrection( [] ), [ '-fspell-checking' ] )


def EnableTypoCorrection_Trivial_test():
  eq_( flags._EnableTypoCorrection( [ '-x', 'c++' ] ),
                                    [ '-x', 'c++', '-fspell-checking' ] )


def EnableTypoCorrection_Reciprocal_test():
  eq_( flags._EnableTypoCorrection( [ '-fno-spell-checking' ] ),
                                    [ '-fno-spell-checking' ] )


def EnableTypoCorrection_ReciprocalOthers_test():
  eq_( flags._EnableTypoCorrection( [ '-x', 'c++', '-fno-spell-checking' ] ),
                                    [ '-x', 'c++', '-fno-spell-checking' ] )


def RemoveUnusedFlags_RemoveFilenameWithoutPrecedingInclude_test():
  def tester( flag ):
    expected = [ 'clang', flag, '/foo/bar', '-isystem/zoo/goo' ]

    eq_( expected,
         flags._RemoveUnusedFlags( expected + to_remove,
                                   filename,
                                   _ShouldAllowWinStyleFlags(
                                     expected + to_remove ) ) )

    eq_( expected,
         flags._RemoveUnusedFlags( expected[ :1 ] + to_remove + expected[ 1: ],
                                   filename,
                                   _ShouldAllowWinStyleFlags(
                                     expected[ :1 ] +
                                     to_remove +
                                     expected[ 1: ] ) ) )

    eq_( expected + expected[ 1: ],
         flags._RemoveUnusedFlags( expected + to_remove + expected[ 1: ],
                                   filename,
                                   _ShouldAllowWinStyleFlags(
                                     expected + to_remove + expected[ 1: ]
                                   ) ) )

  include_flags = [ '-isystem', '-I', '-iquote', '-isysroot', '--sysroot',
                    '-gcc-toolchain', '-include', '-include-pch',
                    '-iframework', '-F', '-imacros', '-idirafter' ]
  to_remove = [ '/moo/boo' ]
  filename = 'file'

  for flag in include_flags:
    yield tester, flag


def RemoveXclangFlags_test():
  expected = [ '-I', '/foo/bar', '-DMACRO=Value' ]
  to_remove = [ '-Xclang', 'load', '-Xclang', 'libplugin.so',
                '-Xclang', '-add-plugin', '-Xclang', 'plugin-name' ]

  eq_( expected,
       flags._RemoveXclangFlags( expected + to_remove ) )

  eq_( expected,
       flags._RemoveXclangFlags( to_remove + expected ) )

  eq_( expected + expected,
       flags._RemoveXclangFlags( expected + to_remove + expected ) )


def AddLanguageFlagWhenAppropriate_Passthrough_test():
  eq_( [ '-foo', '-bar' ],
       flags._AddLanguageFlagWhenAppropriate( [ '-foo', '-bar' ],
                                              _ShouldAllowWinStyleFlags(
                                                [ '-foo', '-bar' ] ) ) )


@WindowsOnly
def AddLanguageFlagWhenAppropriate_CLDriver_Passthrough_test():
  eq_( [ '-foo', '-bar', '--driver-mode=cl' ],
       flags._AddLanguageFlagWhenAppropriate( [ '-foo',
                                                '-bar',
                                                '--driver-mode=cl' ],
                                              _ShouldAllowWinStyleFlags(
                                                [ '-foo',
                                                  '-bar',
                                                  '--driver-mode=cl' ] ) ) )


def _AddLanguageFlagWhenAppropriateTester( compiler, language_flag = [] ):
  to_removes = [
    [],
    [ '/usr/bin/ccache' ],
    [ 'some_command', 'another_command' ]
  ]
  expected = [ '-foo', '-bar' ]

  for to_remove in to_removes:
    eq_( [ compiler ] + language_flag + expected,
         flags._AddLanguageFlagWhenAppropriate( to_remove + [ compiler ] +
                                                expected,
                                                _ShouldAllowWinStyleFlags(
                                                  to_remove + [ compiler ] +
                                                  expected ) ) )


def AddLanguageFlagWhenAppropriate_CCompiler_test():
  compilers = [ 'cc', 'gcc', 'clang', '/usr/bin/cc',
                '/some/other/path', 'some_command' ]

  for compiler in compilers:
    yield _AddLanguageFlagWhenAppropriateTester, compiler


def AddLanguageFlagWhenAppropriate_CppCompiler_test():
  compilers = [ 'c++', 'g++', 'clang++', '/usr/bin/c++',
                '/some/other/path++', 'some_command++',
                'c++-5', 'g++-5.1', 'clang++-3.7.3', '/usr/bin/c++-5',
                'c++-5.11', 'g++-50.1.49', 'clang++-3.12.3', '/usr/bin/c++-10',
                '/some/other/path++-4.9.3', 'some_command++-5.1',
                '/some/other/path++-4.9.31', 'some_command++-5.10' ]

  for compiler in compilers:
    yield _AddLanguageFlagWhenAppropriateTester, compiler, [ '-x', 'c++' ]


def ExtraClangFlags_test():
  flags_object = flags.Flags()
  num_found = 0
  for flag in flags_object.extra_clang_flags:
    if flag.startswith( '-resource-dir=' ):
      ok_( flag.endswith( 'clang_includes' ) )
      num_found += 1

  eq_( 1, num_found )


@MacOnly
@patch( 'ycmd.completers.cpp.flags._GetMacClangVersionList',
        return_value = [ '1.0.0', '7.0.1', '7.0.2', '___garbage__' ] )
@patch( 'ycmd.completers.cpp.flags._MacClangIncludeDirExists',
        side_effect = [ False, True, True, True ] )
def Mac_LatestMacClangIncludes_test( *args ):
  eq_( flags._LatestMacClangIncludes( '/tmp' ),
       [ '/tmp/usr/lib/clang/7.0.2/include' ] )


@MacOnly
def Mac_LatestMacClangIncludes_NoSuchDirectory_test():
  def RaiseOSError( x ):
    raise OSError( x )

  with patch( 'os.listdir', side_effect = RaiseOSError ):
    eq_( flags._LatestMacClangIncludes( '/tmp' ), [] )


@MacOnly
@patch( 'ycmd.completers.cpp.flags._MacClangIncludeDirExists',
        side_effect = [ False, False ] )
def Mac_SelectMacToolchain_None_test( *args ):
  eq_( flags._SelectMacToolchain(), None )


@MacOnly
@patch( 'ycmd.completers.cpp.flags._MacClangIncludeDirExists',
        side_effect = [ True, False ] )
def Mac_SelectMacToolchain_XCode_test( *args ):
  eq_( flags._SelectMacToolchain(),
       '/Applications/Xcode.app/Contents/Developer/Toolchains/'
       'XcodeDefault.xctoolchain' )


@MacOnly
@patch( 'ycmd.completers.cpp.flags._MacClangIncludeDirExists',
        side_effect = [ False, True ] )
def Mac_SelectMacToolchain_CommandLineTools_test( *args ):
  eq_( flags._SelectMacToolchain(), '/Library/Developer/CommandLineTools' )


def CompilationDatabase_NoDatabase_test():
  with TemporaryTestDir() as tmp_dir:
    assert_that(
      calling( flags.Flags().FlagsForFile ).with_args(
        os.path.join( tmp_dir, 'test.cc' ) ),
      raises( NoExtraConfDetected ) )


def CompilationDatabase_FileNotInDatabase_test():
  compile_commands = []
  with TemporaryTestDir() as tmp_dir:
    with TemporaryClangProject( tmp_dir, compile_commands ):
      eq_(
        flags.Flags().FlagsForFile( os.path.join( tmp_dir, 'test.cc' ) ),
        ( [], os.path.join( tmp_dir, 'test.cc' ) ) )


def CompilationDatabase_InvalidDatabase_test():
  with TemporaryTestDir() as tmp_dir:
    with TemporaryClangProject( tmp_dir, 'this is junk' ):
      assert_that(
        calling( flags.Flags().FlagsForFile ).with_args(
          os.path.join( tmp_dir, 'test.cc' ) ),
        raises( NoExtraConfDetected ) )


def CompilationDatabase_UseFlagsFromDatabase_test():
  with TemporaryTestDir() as tmp_dir:
    compile_commands = [
      {
        'directory': tmp_dir,
        'command': 'clang++ -x c++ -I. -I/absolute/path -Wall',
        'file': os.path.join( tmp_dir, 'test.cc' ),
      },
    ]
    with TemporaryClangProject( tmp_dir, compile_commands ):
      assert_that(
        flags.Flags().FlagsForFile(
          os.path.join( tmp_dir, 'test.cc' ),
          add_extra_clang_flags = False )[ 0 ],
        contains( 'clang++',
                  '-x',
                  'c++',
                  '-x',
                  'c++',
                  '-I' + os.path.normpath( tmp_dir ),
                  '-I' + os.path.normpath( '/absolute/path' ),
                  '-Wall' ) )


def CompilationDatabase_UseFlagsFromSameDir_test():
  with TemporaryTestDir() as tmp_dir:
    compile_commands = [
      {
        'directory': tmp_dir,
        'command': 'clang++ -x c++ -Wall',
        'file': os.path.join( tmp_dir, 'test.cc' ),
      },
    ]

    with TemporaryClangProject( tmp_dir, compile_commands ):
      f = flags.Flags()

      # If we now ask for a file _not_ in the DB, we get []
      eq_(
        f.FlagsForFile(
          os.path.join( tmp_dir, 'test1.cc' ),
          add_extra_clang_flags = False ),
        ( [], os.path.join( tmp_dir, 'test1.cc' ) ) )

      # Then, we ask for a file that _is_ in the db. It will cache these flags
      # against the files' directory.
      assert_that(
        f.FlagsForFile(
          os.path.join( tmp_dir, 'test.cc' ),
          add_extra_clang_flags = False )[ 0 ],
        contains( 'clang++',
                  '-x',
                  'c++',
                  '-x',
                  'c++',
                  '-Wall' ) )

      # If we now ask for a file _not_ in the DB, but in the same dir, we should
      # get the same flags
      assert_that(
        f.FlagsForFile(
          os.path.join( tmp_dir, 'test2.cc' ),
          add_extra_clang_flags = False )[ 0 ],
        contains( 'clang++',
                  '-x',
                  'c++',
                  '-x',
                  'c++',
                  '-Wall' ) )


def CompilationDatabase_HeaderFileHeuristic_test():
  with TemporaryTestDir() as tmp_dir:
    compile_commands = [
      {
        'directory': tmp_dir,
        'command': 'clang++ -x c++ -Wall',
        'file': os.path.join( tmp_dir, 'test.cc' ),
      },
    ]

    with TemporaryClangProject( tmp_dir, compile_commands ):
      # If we ask for a header file, it returns the equivalent cc file
      assert_that(
        flags.Flags().FlagsForFile(
          os.path.join( tmp_dir, 'test.h' ),
          add_extra_clang_flags = False )[ 0 ],
        contains( 'clang++',
                  '-x',
                  'c++',
                  '-x',
                  'c++',
                  '-Wall' ) )


def CompilationDatabase_HeaderFileHeuristicNotFound_test():
  with TemporaryTestDir() as tmp_dir:
    compile_commands = [
      {
        'directory': tmp_dir,
        'command': 'clang++ -x c++ -Wall',
        'file': os.path.join( tmp_dir, 'test.cc' ),
      },
    ]

    with TemporaryClangProject( tmp_dir, compile_commands ):
      # If we ask for a header file, it returns the equivalent cc file (if and
      # only if there are flags for that file)
      eq_(
        flags.Flags().FlagsForFile(
          os.path.join( tmp_dir, 'not_in_the_db.h' ),
          add_extra_clang_flags = False )[ 0 ],
        [] )


def CompilationDatabase_ExplicitHeaderFileEntry_test():
  with TemporaryTestDir() as tmp_dir:
    # Have an explicit header file entry which should take priority over the
    # corresponding source file
    compile_commands = [
      {
        'directory': tmp_dir,
        'command': 'clang++ -x c++ -I. -I/absolute/path -Wall',
        'file': os.path.join( tmp_dir, 'test.cc' ),
      },
      {
        'directory': tmp_dir,
        'command': 'clang++ -I/absolute/path -Wall',
        'file': os.path.join( tmp_dir, 'test.h' ),
      },
    ]
    with TemporaryClangProject( tmp_dir, compile_commands ):
      assert_that(
        flags.Flags().FlagsForFile(
          os.path.join( tmp_dir, 'test.h' ),
          add_extra_clang_flags = False )[ 0 ],
        contains( 'clang++',
                  '-x',
                  'c++',
                  '-I' + os.path.normpath( '/absolute/path' ),
                  '-Wall' ) )


def CompilationDatabase_CUDALanguageFlags_test():
  with TemporaryTestDir() as tmp_dir:
    compile_commands = [
      {
        'directory': tmp_dir,
        'command': 'clang++ -Wall {}'.format( './test.cu' ),
        'file': os.path.join( tmp_dir, 'test.cu' ),
      },
    ]

    with TemporaryClangProject( tmp_dir, compile_commands ):
      # If we ask for a header file, it returns the equivalent cu file
      assert_that(
        flags.Flags().FlagsForFile(
          os.path.join( tmp_dir, 'test.h' ),
          add_extra_clang_flags = False )[ 0 ],
        contains( 'clang++',
                  '-x',
                  'cuda',
                  '-Wall' ) )


def _MakeRelativePathsInFlagsAbsoluteTest( test ):
  wd = test[ 'wd' ] if 'wd' in test else '/not_test'
  assert_that(
    flags._MakeRelativePathsInFlagsAbsolute( test[ 'flags' ], wd ),
    contains( *test[ 'expect' ] ) )


def MakeRelativePathsInFlagsAbsolute_test():
  tests = [
    # Already absolute, positional arguments
    {
      'flags':  [ '-isystem', '/test' ],
      'expect': [ '-isystem', os.path.normpath( '/test' ) ],
    },
    {
      'flags':  [ '-I', '/test' ],
      'expect': [ '-I', os.path.normpath( '/test' ) ],
    },
    {
      'flags':  [ '-iquote', '/test' ],
      'expect': [ '-iquote', os.path.normpath( '/test' ) ],
    },
    {
      'flags':  [ '-isysroot', '/test' ],
      'expect': [ '-isysroot', os.path.normpath( '/test' ) ],
    },
    {
      'flags':  [ '-include-pch', '/test' ],
      'expect': [ '-include-pch', os.path.normpath( '/test' ) ],
    },
    {
      'flags':  [ '-idirafter', '/test' ],
      'expect': [ '-idirafter', os.path.normpath( '/test' ) ],
    },

    # Already absolute, single arguments
    {
      'flags':  [ '-isystem/test' ],
      'expect': [ '-isystem' + os.path.normpath( '/test' ) ],
    },
    {
      'flags':  [ '-I/test' ],
      'expect': [ '-I' + os.path.normpath( '/test' ) ],
    },
    {
      'flags':  [ '-iquote/test' ],
      'expect': [ '-iquote' + os.path.normpath( '/test' ) ],
    },
    {
      'flags':  [ '-isysroot/test' ],
      'expect': [ '-isysroot' + os.path.normpath( '/test' ) ],
    },
    {
      'flags':  [ '-include-pch/test' ],
      'expect': [ '-include-pch' + os.path.normpath( '/test' ) ],
    },
    {
      'flags':  [ '-idirafter/test' ],
      'expect': [ '-idirafter' + os.path.normpath( '/test' ) ],
    },


    # Already absolute, double-dash arguments
    {
      'flags':  [ '--isystem=/test' ],
      'expect': [ '--isystem=/test' ],
    },
    {
      'flags':  [ '--I=/test' ],
      'expect': [ '--I=/test' ],
    },
    {
      'flags':  [ '--iquote=/test' ],
      'expect': [ '--iquote=/test' ],
    },
    {
      'flags':  [ '--sysroot=/test' ],
      'expect': [ '--sysroot=' + os.path.normpath( '/test' ) ],
    },
    {
      'flags':  [ '--include-pch=/test' ],
      'expect': [ '--include-pch=/test' ],
    },
    {
      'flags':  [ '--idirafter=/test' ],
      'expect': [ '--idirafter=/test' ],
    },

    # Relative, positional arguments
    {
      'flags':  [ '-isystem', 'test' ],
      'expect': [ '-isystem', os.path.normpath( '/test/test' ) ],
      'wd':     '/test',
    },
    {
      'flags':  [ '-I', 'test' ],
      'expect': [ '-I', os.path.normpath( '/test/test' ) ],
      'wd':     '/test',
    },
    {
      'flags':  [ '-iquote', 'test' ],
      'expect': [ '-iquote', os.path.normpath( '/test/test' ) ],
      'wd':     '/test',
    },
    {
      'flags':  [ '-isysroot', 'test' ],
      'expect': [ '-isysroot', os.path.normpath( '/test/test' ) ],
      'wd':     '/test',
    },
    {
      'flags':  [ '-include-pch', 'test' ],
      'expect': [ '-include-pch', os.path.normpath( '/test/test' ) ],
      'wd':     '/test',
    },
    {
      'flags':  [ '-idirafter', 'test' ],
      'expect': [ '-idirafter', os.path.normpath( '/test/test' ) ],
      'wd':     '/test',
    },

    # Relative, single arguments
    {
      'flags':  [ '-isystemtest' ],
      'expect': [ '-isystem' + os.path.normpath( '/test/test' ) ],
      'wd':     '/test',
    },
    {
      'flags':  [ '-Itest' ],
      'expect': [ '-I' + os.path.normpath( '/test/test' ) ],
      'wd':     '/test',
    },
    {
      'flags':  [ '-iquotetest' ],
      'expect': [ '-iquote' + os.path.normpath( '/test/test' ) ],
      'wd':     '/test',
    },
    {
      'flags':  [ '-isysroottest' ],
      'expect': [ '-isysroot' + os.path.normpath( '/test/test' ) ],
      'wd':     '/test',
    },
    {
      'flags':  [ '-include-pchtest' ],
      'expect': [ '-include-pch' + os.path.normpath( '/test/test' ) ],
      'wd':     '/test',
    },
    {
      'flags':  [ '-idiraftertest' ],
      'expect': [ '-idirafter' + os.path.normpath( '/test/test' ) ],
      'wd':     '/test',
    },

    # Already absolute, double-dash arguments
    {
      'flags':  [ '--isystem=test' ],
      'expect': [ '--isystem=test' ],
      'wd':     '/test',
    },
    {
      'flags':  [ '--I=test' ],
      'expect': [ '--I=test' ],
      'wd':     '/test',
    },
    {
      'flags':  [ '--iquote=test' ],
      'expect': [ '--iquote=test' ],
      'wd':     '/test',
    },
    {
      'flags':  [ '--sysroot=test' ],
      'expect': [ '--sysroot=' + os.path.normpath( '/test/test' ) ],
      'wd':     '/test',
    },
    {
      'flags':  [ '--include-pch=test' ],
      'expect': [ '--include-pch=test' ],
      'wd':     '/test',
    },
    {
      'flags':  [ '--idirafter=test' ],
      'expect': [ '--idirafter=test' ],
      'wd':     '/test',
    },
  ]

  for test in tests:
    yield _MakeRelativePathsInFlagsAbsoluteTest, test


def MakeRelativePathsInFlagsAbsolute_IgnoreUnknown_test():
  tests = [
    {
      'flags': [
        'ignored',
        '-isystem',
        '/test',
        '-ignored',
        '-I',
        '/test',
        '--ignored=ignored'
      ],
      'expect': [
        'ignored',
        '-isystem', os.path.normpath( '/test' ),
        '-ignored',
        '-I', os.path.normpath( '/test' ),
        '--ignored=ignored'
      ]
    },
    {
      'flags': [
        'ignored',
        '-isystem/test',
        '-ignored',
        '-I/test',
        '--ignored=ignored'
      ],
      'expect': [
        'ignored',
        '-isystem' + os.path.normpath( '/test' ),
        '-ignored',
        '-I' + os.path.normpath( '/test/' ),
        '--ignored=ignored'
      ]
    },
    {
      'flags': [
        'ignored',
        '--isystem=/test',
        '-ignored',
        '--I=/test',
        '--ignored=ignored'
      ],
      'expect': [
        'ignored',
        '--isystem=/test',
        '-ignored',
        '--I=/test',
        '--ignored=ignored'
      ]
    },
    {
      'flags': [
        'ignored',
        '-isystem', 'test',
        '-ignored',
        '-I', 'test',
        '--ignored=ignored'
      ],
      'expect': [
        'ignored',
        '-isystem', os.path.normpath( '/test/test' ),
        '-ignored',
        '-I', os.path.normpath( '/test/test' ),
        '--ignored=ignored'
      ],
      'wd': '/test',
    },
    {
      'flags': [
        'ignored',
        '-isystemtest',
        '-ignored',
        '-Itest',
        '--ignored=ignored'
      ],
      'expect': [
        'ignored',
        '-isystem' + os.path.normpath( '/test/test' ),
        '-ignored',
        '-I' + os.path.normpath( '/test/test' ),
        '--ignored=ignored'
      ],
      'wd': '/test',
    },
    {
      'flags': [
        'ignored',
        '--isystem=test',
        '-ignored',
        '--I=test',
        '--ignored=ignored',
        '--sysroot=test'
      ],
      'expect': [
        'ignored',
        '--isystem=test',
        '-ignored',
        '--I=test',
        '--ignored=ignored',
        '--sysroot=' + os.path.normpath( '/test/test' ),
      ],
      'wd': '/test',
    },
  ]

  for test in tests:
    yield _MakeRelativePathsInFlagsAbsoluteTest, test


def MakeRelativePathsInFlagsAbsolute_NoWorkingDir_test():
  yield _MakeRelativePathsInFlagsAbsoluteTest, {
    'flags': [ 'list', 'of', 'flags', 'not', 'changed', '-Itest' ],
    'expect': [ 'list', 'of', 'flags', 'not', 'changed', '-Itest' ],
    'wd': ''
  }
