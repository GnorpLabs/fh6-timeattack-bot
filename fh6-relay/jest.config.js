module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/tests'],
  moduleNameMapper: {
    '^../src/shared/(.*)$': '<rootDir>/src/shared/$1',
    '^../src/main/(.*)$': '<rootDir>/src/main/$1',
  },
};
