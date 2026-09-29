import hardhatEthers from "@nomicfoundation/hardhat-ethers";
/** @type import('hardhat/config').HardhatUserConfig */
export default {
  plugins: [hardhatEthers],
  solidity: { version: "0.8.24", settings: { optimizer: { enabled: true, runs: 200 } } },
};
