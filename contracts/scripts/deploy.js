/**
 * MucizeCoin (MZC) — Deploy Script
 * Mimar Yonus KALKAN — mucizeWORK Ekosistemi
 *
 * Usage:
 *   npx hardhat run scripts/deploy.js --network sepolia
 *   npx hardhat run scripts/deploy.js --network mainnet
 */
const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deployer:", deployer.address);
  console.log(
    "Balance :",
    hre.ethers.formatEther(
      await hre.ethers.provider.getBalance(deployer.address)
    ),
    "ETH"
  );

  // 1. Deploy MucizeCoin
  console.log("\n--- Deploying MucizeCoin ---");
  const MucizeCoin = await hre.ethers.getContractFactory("MucizeCoin");
  const mzc = await MucizeCoin.deploy(deployer.address);
  await mzc.waitForDeployment();
  const mzcAddr = await mzc.getAddress();
  console.log("MucizeCoin deployed to:", mzcAddr);
  console.log(
    "Total supply:",
    hre.ethers.formatEther(await mzc.totalSupply()),
    "MZC"
  );

  // 2. Deploy MZCVesting
  console.log("\n--- Deploying MZCVesting ---");
  const MZCVesting = await hre.ethers.getContractFactory("MZCVesting");
  const vesting = await MZCVesting.deploy(mzcAddr, deployer.address);
  await vesting.waitForDeployment();
  const vestingAddr = await vesting.getAddress();
  console.log("MZCVesting deployed to:", vestingAddr);

  // 3. Summary
  console.log("\n========================================");
  console.log("  MucizeCoin (MZC) Deploy Complete");
  console.log("========================================");
  console.log("Token   :", mzcAddr);
  console.log("Vesting :", vestingAddr);
  console.log("Owner   :", deployer.address);
  console.log("Network :", hre.network.name);
  console.log("========================================");

  // 4. Verify (skip on local/hardhat network)
  if (hre.network.name !== "hardhat" && hre.network.name !== "localhost") {
    console.log("\nWaiting for block confirmations before verify...");
    await new Promise((r) => setTimeout(r, 30_000));

    try {
      await hre.run("verify:verify", {
        address: mzcAddr,
        constructorArguments: [deployer.address],
      });
      console.log("MucizeCoin verified!");
    } catch (e) {
      console.log("MucizeCoin verify error:", e.message);
    }

    try {
      await hre.run("verify:verify", {
        address: vestingAddr,
        constructorArguments: [mzcAddr, deployer.address],
      });
      console.log("MZCVesting verified!");
    } catch (e) {
      console.log("MZCVesting verify error:", e.message);
    }
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
