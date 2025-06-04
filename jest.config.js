const { pathsToModuleNameMapper } = require('ts-jest/utils')
const tsconfig = require('./tsconfig.json')

module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src', '<rootDir>/tests'],
  testMatch: ['**/?(*.)+(spec|test).[tj]s?(x)'],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
  moduleNameMapper: pathsToModuleNameMapper(tsconfig.compilerOptions.paths || {}, { prefix: '<rootDir>/src/' }),
  collectCoverage: true,
  coverageDirectory: '<rootDir>/coverage',
  coverageReporters: ['text', 'lcov', 'json'],
  globals: {
    'ts-jest': {
      tsconfig: 'tsconfig.json',
      diagnostics: false
    }
  },
  transform: {
    '^.+\\.(ts|tsx)$': 'ts-jest'
  },
  testTimeout: 30000,
  setupFilesAfterEnv: []
}