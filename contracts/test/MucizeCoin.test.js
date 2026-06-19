const { expect } = require("chai");
const { ethers } = require("hardhat");
const { loadFixture, time } = require("@nomicfoundation/hardhat-toolbox/network-helpers");

describe("MucizeCoin", function () {
  async function deployFixture() {
    const [owner, alice, bob] = await ethers.getSigners();
    const MucizeCoin = await ethers.getContractFactory("MucizeCoin");
    const mzc = await MucizeCoin.deploy(owner.address);
    return { mzc, owner, alice, bob };
  }

  describe("Deployment", function () {
    it("should set correct name and symbol", async function () {
      const { mzc } = await loadFixture(deployFixture);
      expect(await mzc.name()).to.equal("MucizeCoin");
      expect(await mzc.symbol()).to.equal("MZC");
    });

    it("should mint total supply to owner", async function () {
      const { mzc, owner } = await loadFixture(deployFixture);
      const totalSupply = await mzc.totalSupply();
      expect(totalSupply).to.equal(ethers.parseEther("1000000000"));
      expect(await mzc.balanceOf(owner.address)).to.equal(totalSupply);
    });

    it("should set correct owner", async function () {
      const { mzc, owner } = await loadFixture(deployFixture);
      expect(await mzc.owner()).to.equal(owner.address);
    });

    it("should have 18 decimals", async function () {
      const { mzc } = await loadFixture(deployFixture);
      expect(await mzc.decimals()).to.equal(18);
    });

    it("should have MAX_SUPPLY constant", async function () {
      const { mzc } = await loadFixture(deployFixture);
      expect(await mzc.MAX_SUPPLY()).to.equal(ethers.parseEther("1000000000"));
    });
  });

  describe("Transfer", function () {
    it("should transfer tokens", async function () {
      const { mzc, owner, alice } = await loadFixture(deployFixture);
      const amount = ethers.parseEther("1000");
      await mzc.transfer(alice.address, amount);
      expect(await mzc.balanceOf(alice.address)).to.equal(amount);
    });

    it("should fail transfer when paused", async function () {
      const { mzc, owner, alice } = await loadFixture(deployFixture);
      await mzc.pause();
      await expect(
        mzc.transfer(alice.address, ethers.parseEther("100"))
      ).to.be.revertedWithCustomError(mzc, "EnforcedPause");
    });
  });

  describe("Mint", function () {
    it("should not allow minting beyond MAX_SUPPLY", async function () {
      const { mzc, owner, alice } = await loadFixture(deployFixture);
      await expect(mzc.mint(alice.address, 1)).to.be.revertedWith("MZC: cap exceeded");
    });

    it("should allow minting after burn (within cap)", async function () {
      const { mzc, owner, alice } = await loadFixture(deployFixture);
      const burnAmount = ethers.parseEther("1000");
      await mzc.burn(burnAmount);
      await mzc.mint(alice.address, burnAmount);
      expect(await mzc.balanceOf(alice.address)).to.equal(burnAmount);
    });

    it("should reject mint from non-owner", async function () {
      const { mzc, alice } = await loadFixture(deployFixture);
      await expect(
        mzc.connect(alice).mint(alice.address, 1)
      ).to.be.revertedWithCustomError(mzc, "OwnableUnauthorizedAccount");
    });
  });

  describe("Burn", function () {
    it("should burn tokens and reduce total supply", async function () {
      const { mzc } = await loadFixture(deployFixture);
      const burnAmount = ethers.parseEther("50000000");
      await mzc.burn(burnAmount);
      expect(await mzc.totalSupply()).to.equal(
        ethers.parseEther("1000000000") - burnAmount
      );
    });
  });

  describe("Pause", function () {
    it("should pause and unpause by owner", async function () {
      const { mzc, owner, alice } = await loadFixture(deployFixture);
      await mzc.pause();
      expect(await mzc.paused()).to.be.true;
      await mzc.unpause();
      expect(await mzc.paused()).to.be.false;
      await mzc.transfer(alice.address, ethers.parseEther("100"));
      expect(await mzc.balanceOf(alice.address)).to.equal(ethers.parseEther("100"));
    });

    it("should reject pause from non-owner", async function () {
      const { mzc, alice } = await loadFixture(deployFixture);
      await expect(
        mzc.connect(alice).pause()
      ).to.be.revertedWithCustomError(mzc, "OwnableUnauthorizedAccount");
    });
  });

  describe("Ownership (Ownable2Step)", function () {
    it("should transfer ownership in two steps", async function () {
      const { mzc, owner, alice } = await loadFixture(deployFixture);
      await mzc.transferOwnership(alice.address);
      expect(await mzc.owner()).to.equal(owner.address);
      await mzc.connect(alice).acceptOwnership();
      expect(await mzc.owner()).to.equal(alice.address);
    });
  });
});

describe("MZCVesting", function () {
  const MONTH = 30 * 24 * 60 * 60;

  async function deployVestingFixture() {
    const [owner, team, investor, advisor] = await ethers.getSigners();
    const MucizeCoin = await ethers.getContractFactory("MucizeCoin");
    const mzc = await MucizeCoin.deploy(owner.address);

    const MZCVesting = await ethers.getContractFactory("MZCVesting");
    const vesting = await MZCVesting.deploy(await mzc.getAddress(), owner.address);

    await mzc.approve(await vesting.getAddress(), ethers.parseEther("1000000000"));

    const now = await time.latest();
    return { mzc, vesting, owner, team, investor, advisor, now };
  }

  describe("Schedule Creation", function () {
    it("should create a team vesting schedule (6m cliff + 18m vest)", async function () {
      const { vesting, team, now } = await loadFixture(deployVestingFixture);
      const amount = ethers.parseEther("200000000");
      await vesting.createSchedule(team.address, amount, now, 6 * MONTH, 18 * MONTH);
      const schedule = await vesting.getSchedule(team.address, 0);
      expect(schedule.totalAmount).to.equal(amount);
      expect(schedule.cliffDuration).to.equal(6 * MONTH);
      expect(schedule.vestingDuration).to.equal(18 * MONTH);
      expect(schedule.revoked).to.be.false;
    });

    it("should create an investor vesting schedule (3m cliff + 12m vest)", async function () {
      const { vesting, investor, now } = await loadFixture(deployVestingFixture);
      const amount = ethers.parseEther("150000000");
      await vesting.createSchedule(investor.address, amount, now, 3 * MONTH, 12 * MONTH);
      expect(await vesting.scheduleCount(investor.address)).to.equal(1);
    });

    it("should reject schedule with zero address", async function () {
      const { vesting, now } = await loadFixture(deployVestingFixture);
      await expect(
        vesting.createSchedule(ethers.ZeroAddress, ethers.parseEther("100"), now, 0, 12 * MONTH)
      ).to.be.revertedWith("Vesting: zero address");
    });

    it("should reject schedule with zero amount", async function () {
      const { vesting, team, now } = await loadFixture(deployVestingFixture);
      await expect(
        vesting.createSchedule(team.address, 0, now, 0, 12 * MONTH)
      ).to.be.revertedWith("Vesting: zero amount");
    });

    it("should reject from non-owner", async function () {
      const { vesting, team, now } = await loadFixture(deployVestingFixture);
      await expect(
        vesting.connect(team).createSchedule(team.address, ethers.parseEther("100"), now, 0, 12 * MONTH)
      ).to.be.revertedWithCustomError(vesting, "OwnableUnauthorizedAccount");
    });
  });

  describe("Vesting Release", function () {
    it("should not release before cliff", async function () {
      const { vesting, team, now } = await loadFixture(deployVestingFixture);
      await vesting.createSchedule(team.address, ethers.parseEther("200000000"), now, 6 * MONTH, 18 * MONTH);
      await time.increase(3 * MONTH);
      expect(await vesting.releasable(team.address, 0)).to.equal(0);
      await expect(vesting.connect(team).release(0)).to.be.revertedWith("Vesting: nothing to release");
    });

    it("should release partially after cliff + some vesting", async function () {
      const { mzc, vesting, team, now } = await loadFixture(deployVestingFixture);
      const totalAmount = ethers.parseEther("180000000");
      await vesting.createSchedule(team.address, totalAmount, now, 6 * MONTH, 18 * MONTH);
      await time.increase(6 * MONTH + 9 * MONTH);
      const releasableAmt = await vesting.releasable(team.address, 0);
      expect(releasableAmt).to.be.gt(0);
      await vesting.connect(team).release(0);
      expect(await mzc.balanceOf(team.address)).to.be.gt(0);
    });

    it("should release all after full vesting period", async function () {
      const { mzc, vesting, team, now } = await loadFixture(deployVestingFixture);
      const totalAmount = ethers.parseEther("100000000");
      await vesting.createSchedule(team.address, totalAmount, now, 6 * MONTH, 18 * MONTH);
      await time.increase(6 * MONTH + 18 * MONTH + 1);
      await vesting.connect(team).release(0);
      expect(await mzc.balanceOf(team.address)).to.equal(totalAmount);
    });

    it("should handle ecosystem schedule with no cliff", async function () {
      const { vesting, team, now } = await loadFixture(deployVestingFixture);
      const totalAmount = ethers.parseEther("300000000");
      await vesting.createSchedule(team.address, totalAmount, now, 0, 12 * MONTH);
      await time.increase(6 * MONTH);
      const releasable = await vesting.releasable(team.address, 0);
      const expected = totalAmount / 2n;
      const tolerance = ethers.parseEther("1000");
      expect(releasable).to.be.closeTo(expected, tolerance);
    });
  });

  describe("Revocation", function () {
    it("should revoke and return unvested tokens to owner", async function () {
      const { mzc, vesting, owner, team, now } = await loadFixture(deployVestingFixture);
      const totalAmount = ethers.parseEther("200000000");
      await vesting.createSchedule(team.address, totalAmount, now, 6 * MONTH, 18 * MONTH);
      await time.increase(6 * MONTH + 9 * MONTH);
      await vesting.revoke(team.address, 0);
      const schedule = await vesting.getSchedule(team.address, 0);
      expect(schedule.revoked).to.be.true;
      expect(await mzc.balanceOf(team.address)).to.be.gt(0);
    });

    it("should reject revoke from non-owner", async function () {
      const { vesting, team, now } = await loadFixture(deployVestingFixture);
      await vesting.createSchedule(team.address, ethers.parseEther("100"), now, 0, 12 * MONTH);
      await expect(
        vesting.connect(team).revoke(team.address, 0)
      ).to.be.revertedWithCustomError(vesting, "OwnableUnauthorizedAccount");
    });

    it("should reject double revoke", async function () {
      const { vesting, team, now } = await loadFixture(deployVestingFixture);
      await vesting.createSchedule(team.address, ethers.parseEther("100"), now, 0, 12 * MONTH);
      await vesting.revoke(team.address, 0);
      await expect(vesting.revoke(team.address, 0)).to.be.revertedWith("Vesting: already revoked");
    });
  });
});
